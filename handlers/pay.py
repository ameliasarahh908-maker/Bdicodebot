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

    loading = None
    try:
        loading = await call.message.answer(
            "⏳ <b>Membuat QRIS...</b>\n\nMohon tunggu sebentar.",
            parse_mode="HTML"
        )
    except:
        pass

    async def fail(msg):
        logger.warning("❌ FAIL: %s", msg)
        try:
            if loading:
                await loading.delete()
        except:
            pass
        return await call.answer(msg, show_alert=True)

    lock_key = f"paylock:{user_id}:{code}"

    try:
        lock_ok = await safe_set(lock_key, "1", ex=PAY_LOCK_TTL, nx=True)
    except:
        lock_ok = True

    if not lock_ok:
        return await fail("⏳ Tunggu sebentar...")

    try:
        # =========================
        # GET FILE
        # =========================
        file = await fetchrow(
            """
            SELECT owner_id, price, is_paid
            FROM files
            WHERE code=$1
            """,
            code
        )

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

        if existing:
            if existing["status"] == "paid":
                return await fail("Sudah dibeli")

            if existing["status"] == "pending":
                invoice_id = existing["payment_id"]

                kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text="✅ Cek Pembayaran",
                            callback_data=f"check:{invoice_id}"
                        )],
                        [InlineKeyboardButton(
                            text="❌ Batalkan",
                            callback_data=f"cancel:{invoice_id}"
                        )]
                    ]
                )

                await call.message.answer(
                    "⚠️ <b>Masih ada pembayaran pending</b>\n\n"
                    f"🧾 Invoice: <code>{invoice_id}</code>",
                    parse_mode="HTML",
                    reply_markup=kb
                )
                return

        # =========================
        # CREATE PAYMENT
        # =========================
        try:
            data = await BayarGG.create_payment(
                amount=price,
                description=f"File {code}",
                customer_name=call.from_user.full_name
            )
        except Exception as e:
            logger.exception("❌ CREATE PAYMENT ERROR: %s", e)
            return await fail("❌ Payment API error")

        if not data or isinstance(data, str):
            return await fail("❌ Gagal membuat pembayaran")

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
            return await fail("❌ Invoice tidak dibuat")

        if not qr_string:
            return await fail("❌ QRIS tidak tersedia")

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

        try:
            await safe_set(
                f"invoice:{invoice_id}",
                f"{user_id}:{code}:pending",
                ex=INVOICE_TTL
            )
        except:
            pass

        # =========================
        # GENERATE QR
        # =========================
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

        try:
            await call.message.delete()
        except:
            pass

        # =========================
        # SEND QR
        # =========================
        msg = None

        for _ in range(3):
            try:
                msg = await call.message.answer_photo(
                    BufferedInputFile(buf.getvalue(), filename="qris.png"),
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
                logger.exception("❌ Send QR error: %s", e)
                await asyncio.sleep(1)

        if not msg:
            return await fail("❌ Gagal kirim QR")

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
        logger.exception("💥 PAY ERROR")
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


# =========================
# CHECK PAYMENT (FIX 1X DOANG)
# =========================
@router.callback_query(F.data.startswith("check:"))
async def check_payment(call: CallbackQuery):
    invoice_id = call.data.split(":")[1]

    await call.answer("🔄 Mengecek pembayaran...")

    data = await BayarGG.check_payment(invoice_id)

    if not data:
        return await call.answer("❌ Gagal cek pembayaran", show_alert=True)

    status = data.get("status") or data.get("payment_status")

    if status == "paid":
        await execute(
            "UPDATE file_purchases SET status='paid' WHERE payment_id=$1",
            invoice_id
        )

        return await call.message.answer(
            "✅ <b>Pembayaran berhasil!</b>\nFile akan dikirim...",
            parse_mode="HTML"
        )

    elif status == "pending":
        return await call.answer("⏳ Masih menunggu pembayaran", show_alert=True)

    else:
        return await call.answer(f"❌ Status: {status}", show_alert=True)
