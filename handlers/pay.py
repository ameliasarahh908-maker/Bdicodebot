import asyncio
import qrcode
from io import BytesIO
import logging

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BufferedInputFile
)

from database import fetchrow, execute
from utils.bayargg import BayarGG
from utils.redis_client import safe_set, safe_delete

logger = logging.getLogger(__name__)
router = Router()

PAY_LOCK_TTL = 30
INVOICE_TTL = 3600


@router.callback_query(F.data.startswith("pay:"))
async def pay_file(call: CallbackQuery):

    user_id = call.from_user.id
    code = call.data.split(":")[1]

    logger.info("🔥 PAY START | user=%s file=%s", user_id, code)

    await call.answer("⏳ Memproses pembayaran...")

    # =========================
    # LOADING SAFE
    # =========================
    loading = None
    try:
        loading = await call.message.answer(
            "⏳ <b>Membuat QRIS...</b>\n\nMohon tunggu sebentar.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error("❌ Gagal kirim loading: %s", e)

    async def fail(msg):
        logger.warning("❌ FAIL: %s", msg)
        try:
            if loading:
                await loading.delete()
        except:
            pass
        return await call.answer(msg, show_alert=True)

    lock_key = f"paylock:{user_id}:{code}"

    # =========================
    # REDIS LOCK
    # =========================
    try:
        lock_ok = await safe_set(lock_key, "1", ex=PAY_LOCK_TTL, nx=True)
    except Exception:
        logger.exception("❌ Redis lock error")
        lock_ok = True

    if not lock_ok:
        return await fail("⏳ Tunggu sebentar...")

    try:
        # =========================
        # GET FILE
        # =========================
        logger.info("📦 FETCH FILE")

        file = await fetchrow(
            """
            SELECT owner_id, price, is_paid
            FROM files
            WHERE code=$1
            """,
            code
        )

        logger.info("📦 FILE RESULT: %s", file)

        if not file:
            return await fail("❌ File tidak ditemukan")

        if not file["is_paid"]:
            return await fail("File gratis")

        if file["owner_id"] == user_id:
            return await fail("Owner tidak perlu bayar")

        price = file["price"] or 0

        if price <= 0:
            return await fail("❌ Harga tidak valid")

        # =========================
        # CHECK EXISTING
        # =========================
        logger.info("🔍 CHECK EXISTING PAYMENT")

        existing = await fetchrow(
            """
            SELECT payment_id, status
            FROM file_purchases
            WHERE user_id=$1 AND file_code=$2
            ORDER BY id DESC
            LIMIT 1
            """,
            user_id,
            code
        )

        logger.info("🔍 EXISTING: %s", existing)

        if existing:
            if existing["status"] == "paid":
                return await fail("Sudah dibeli")

            if existing["status"] == "pending":
                return await fail(
                    "⚠️ Masih ada pembayaran pending.\nSelesaikan atau cancel dulu."
                )

        # =========================
        # CREATE PAYMENT
        # =========================
        logger.info("🚀 CREATE PAYMENT START")

        try:
            data = await BayarGG.create_payment(
                amount=price,
                description=f"File {code}",
                customer_name=call.from_user.full_name
            )
        except Exception as e:
            logger.exception("❌ ERROR CREATE PAYMENT: %s", e)
            return await fail("❌ Payment API error")

        logger.info("✅ CREATE PAYMENT RESULT: %s", data)

        if not data or isinstance(data, str):
            return await fail("❌ Gagal membuat pembayaran (no response)")

        # FLEXIBLE PARSING (ANTI ERROR FORMAT)
        invoice_id = (
            data.get("invoice_id")
            or data.get("invoice")
            or data.get("id")
        )

        qr_string = (
            data.get("qris_string")
            or data.get("qr_string")
            or data.get("qr")
        )

        final_amount = (
            data.get("final_amount")
            or data.get("amount")
            or price
        )

        if not invoice_id:
            logger.error("❌ INVOICE KOSONG | %s", data)
            return await fail("❌ Invoice tidak dibuat")

        if not qr_string:
            logger.error("❌ QR STRING KOSONG | %s", data)
            return await fail("❌ QRIS tidak tersedia")

        logger.info("✅ PAYMENT CREATED | invoice=%s", invoice_id)

        # =========================
        # SAVE PAYMENT
        # =========================
        await execute(
            """
            INSERT INTO file_purchases
            (user_id, file_code, owner_id, paid_price, payment_id, status, created_at)
            VALUES ($1,$2,$3,$4,$5,'pending',NOW())
            """,
            user_id,
            code,
            file["owner_id"],
            price,
            invoice_id
        )

        # =========================
        # REDIS TRACK
        # =========================
        try:
            await safe_set(
                f"invoice:{invoice_id}",
                f"{user_id}:{code}:pending",
                ex=INVOICE_TTL
            )
        except Exception:
            logger.exception("❌ Redis invoice failed")

        # =========================
        # GENERATE QR
        # =========================
        logger.info("🧾 GENERATE QR")

        qr = qrcode.make(qr_string)
        buf = BytesIO()
        qr.save(buf, format="PNG")
        buf.seek(0)

        if buf.getbuffer().nbytes == 0:
            return await fail("❌ QR gagal dibuat")

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="✅ Check Payment",
                    callback_data=f"check:{invoice_id}"
                )],
                [InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data=f"cancel:{invoice_id}"
                )]
            ]
        )

        # =========================
        # DELETE OLD MESSAGE
        # =========================
        try:
            await call.message.delete()
        except Exception:
            logger.warning("⚠️ Gagal delete message lama")

        # =========================
        # SEND QR
        # =========================
        logger.info("📤 SEND QR")

        msg = None

        for i in range(3):
            try:
                msg = await call.message.answer_photo(
                    BufferedInputFile(
                        buf.getvalue(),
                        filename="qris.png"
                    ),
                    caption=(
                        "💳 <b>PAYMENT QRIS</b>\n\n"
                        f"🧾 Invoice : <code>{invoice_id}</code>\n"
                        f"💰 Total Bayar : Rp {final_amount:,}\n\n"
                        "Scan QR untuk melakukan pembayaran."
                    ).replace(",", "."),
                    parse_mode="HTML",
                    reply_markup=kb
                )
                break
            except Exception as e:
                logger.exception("❌ Send QR gagal (retry %s): %s", i, e)
                await asyncio.sleep(1)

        if not msg:
            return await fail("❌ Gagal kirim QR")

        # =========================
        # SAVE MESSAGE
        # =========================
        await execute(
            """
            UPDATE file_purchases
            SET qr_message_id=$1, qr_chat_id=$2
            WHERE payment_id=$3
            """,
            msg.message_id,
            msg.chat.id,
            invoice_id
        )

        logger.info("🎉 QR SENT SUCCESS | %s", invoice_id)

    except Exception:
        logger.exception("💥 PAY ERROR | user=%s file=%s", user_id, code)
        await call.answer("❌ Terjadi error", show_alert=True)

    finally:
        try:
            if loading:
                await loading.delete()
        except:
            pass

        try:
            await safe_delete(lock_key)
        except:
            pass
