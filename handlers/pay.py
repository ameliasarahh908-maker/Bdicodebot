import asyncio
import json
import logging
import qrcode

from io import BytesIO

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BufferedInputFile
)

from utils.redis_client import safe_set, safe_get, safe_delete
from database import fetchrow, execute
from utils.bayargg import BayarGG
from config import STORAGE_CHANNEL_ID, NOTIF_CHANNEL_ID


logger = logging.getLogger(__name__)

router = Router()

def mask_user_id(user_id: int) -> str:
    uid = str(user_id)

    if len(uid) <= 4:
        return "****"

    return uid[:2] + "****" + uid[-2:]

async def send_upgrade_notif(bot, user_id: int, tier: str):
    try:
        masked = mask_user_id(user_id)

        if tier.lower() == "vip":
            text = (
                "🌟 <b>VIP UPGRADE</b>\n\n"
                f"👤 User: <code>{masked}</code>\n"
                "📦 Paket: VIP"
            )

        elif tier.lower() == "vvip":
            text = (
                "👑 <b>VVIP UPGRADE</b>\n\n"
                f"👤 User: <code>{masked}</code>\n"
                "📦 Paket: VVIP"
            )

        else:
            return

        await bot.send_message(
            chat_id=NOTIF_CHANNEL_ID,
            text=text,
            parse_mode="HTML"
        )

    except Exception:
        logger.exception("UPGRADE NOTIF ERROR")

PAY_LOCK_TTL = 30
INVOICE_TTL = 3600

CHECK_LOCK = set()


# =========================
# MEDIA PAGINATION
# =========================

PER_PAGE = 10


def media_keyboard(invoice, page, total):

    max_page = (total + PER_PAGE - 1) // PER_PAGE

    buttons = []

    nav = []

    if page > 1:
        nav.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=f"mpage:{invoice}:{page-1}"
            )
        )

    nav.append(
        InlineKeyboardButton(
            text=f"{page}/{max_page}",
            callback_data="none"
        )
    )

    if page < max_page:
        nav.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=f"mpage:{invoice}:{page+1}"
            )
        )

    buttons.append(nav)

    buttons.append(
        [
            InlineKeyboardButton(
                text="📤 Kirim Halaman",
                callback_data=f"sendpage:{invoice}:{page}"
            )
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                text="📦 Kirim Semua",
                callback_data=f"sendall:{invoice}"
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


@router.callback_query(F.data.startswith("pay:"))
async def pay_file(call: CallbackQuery):

    user_id = call.from_user.id
    code = call.data.split(":")[1]

    await call.answer("⏳ Membuat pembayaran...")

    loading = await call.message.answer(
        "⏳ <b>Membuat QRIS...</b>",
        parse_mode="HTML"
    )

    lock_key = f"paylock:{user_id}:{code}"

    lock = await safe_set(
        lock_key,
        "1",
        ex=PAY_LOCK_TTL,
        nx=True
    )

    if not lock:
        await loading.delete()
        return await call.answer(
            "⏳ Tunggu sebentar",
            show_alert=True
        )


    try:

        file = await fetchrow(
            """
            SELECT *
            FROM files
            WHERE code=$1
            """,
            code
        )


        if not file:
            return await call.answer(
                "❌ File tidak ditemukan",
                show_alert=True
            )


        if not file["is_paid"]:
            return await call.answer(
                "File gratis",
                show_alert=True
            )


        if file["owner_id"] == user_id:
            return await call.answer(
                "Owner tidak perlu bayar",
                show_alert=True
            )


        price = file["price"] or 0


        if price <= 0:
            return await call.answer(
                "Harga file tidak valid",
                show_alert=True
            )


        old = await fetchrow(
            """
            SELECT payment_id,status
            FROM file_purchases
            WHERE user_id=$1
            AND file_code=$2
            ORDER BY id DESC
            LIMIT 1
            """,
            user_id,
            code
        )


        if old:

            if old["status"] == "paid":
                return await call.answer(
                    "✅ File sudah dibeli",
                    show_alert=True
                )


            if old["status"] == "pending":

                invoice = old["payment_id"]

                kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🔄 Cek Pembayaran",
                                callback_data=f"check:{invoice}"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="❌ Batalkan",
                                callback_data=f"cancel:{invoice}"
                            )
                        ]
                    ]
                )


                await call.message.answer(
                    f"⚠️ <b>Pembayaran masih pending</b>\n\n"
                    f"Invoice:\n<code>{invoice}</code>",
                    parse_mode="HTML",
                    reply_markup=kb
                )

                return



        data = await BayarGG.create_payment(
            amount=price,
            description=f"File {code}",
            customer_name=call.from_user.full_name
        )


        if not data:
            return await call.answer(
                "❌ Gagal membuat pembayaran",
                show_alert=True
            )


        invoice = data.get("invoice_id")

        qr_string = data.get("qris_string")


        amount = (
            data.get("final_amount")
            or data.get("amount")
            or price
        )


        if not invoice or not qr_string:
            return await call.answer(
                "❌ QRIS tidak tersedia",
                show_alert=True
            )



        await execute(
            """
            INSERT INTO file_purchases
            (
                user_id,
                file_code,
                owner_id,
                paid_price,
                payment_id,
                status,
                created_at
            )
            VALUES
            ($1,$2,$3,$4,$5,'pending',NOW())
            """,
            user_id,
            code,
            file["owner_id"],
            price,
            invoice
        )


        await safe_set(
            f"invoice:{invoice}",
            f"{user_id}:{code}",
            ex=INVOICE_TTL
        )


        qr = qrcode.make(qr_string)

        buf = BytesIO()

        qr.save(
            buf,
            "PNG"
        )

        buf.seek(0)



        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔄 Cek Pembayaran",
                        callback_data=f"check:{invoice}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Batalkan",
                        callback_data=f"cancel:{invoice}"
                    )
                ]
            ]
        )


        try:
            await call.message.delete()
        except:
            pass


        msg = await call.message.answer_photo(
            BufferedInputFile(
                buf.getvalue(),
                filename="qris.png"
            ),
            caption=(
                f"💳 <b>PAYMENT QRIS</b>\n\n"
                f"Invoice:\n<code>{invoice}</code>\n\n"
                f"Total:\nRp {amount:,}\n\n"
                f"Scan QR untuk membayar."
            ).replace(",", "."),
            parse_mode="HTML",
            reply_markup=kb
        )


        await execute(
            """
            UPDATE file_purchases
            SET qr_message_id=$1,
                qr_chat_id=$2
            WHERE payment_id=$3
            """,
            msg.message_id,
            msg.chat.id,
            invoice
        )


    except Exception:

        logger.exception("PAY ERROR")

        await call.answer(
            "❌ Error pembayaran",
            show_alert=True
        )


    finally:

        try:
            await loading.delete()
        except:
            pass


        await safe_delete(lock_key)

@router.callback_query(F.data.startswith("check:"))
async def check_payment(call: CallbackQuery):

    invoice = call.data.split(":")[1]

    if invoice in CHECK_LOCK:
        return await call.answer("⏳ Sedang diproses...", show_alert=True)

    CHECK_LOCK.add(invoice)

    try:
        await call.answer("🔄 Mengecek pembayaran...")

        result = await BayarGG.check_payment(invoice)

        logger.info("CHECK RESULT %s", result)

        if not result:
            return await call.answer("❌ Gagal cek pembayaran", show_alert=True)

        status = result.get("status") or result.get("payment_status")

        if status != "paid":
            return await call.answer("⏳ Belum dibayar", show_alert=True)

        purchase = await fetchrow(
            "SELECT * FROM file_purchases WHERE payment_id=$1",
            invoice
        )

        if not purchase:
            return await call.message.answer("❌ Data pembayaran tidak ditemukan")

        if purchase["status"] == "paid":
            return await call.answer("✅ File sudah dikirim", show_alert=True)

        file = await fetchrow(
            "SELECT * FROM files WHERE code=$1",
            purchase["file_code"]
        )

        if not file:
            return await call.message.answer("❌ File tidak ditemukan")

        # =========================
        # 🔥 AMBIL & FILTER MEDIA
        # =========================
        media_data = file["media"]

        if isinstance(media_data, str):
            media_list = json.loads(media_data)
        else:
            media_list = media_data

        media_list = [
            m for m in media_list
            if isinstance(m, dict) and m.get("message_id")
        ]

        if not media_list:
            return await call.message.answer("❌ Media kosong")

        # =========================
        # 🔥 SAVE KE REDIS
        # =========================
        await safe_set(
            f"paidmedia:{invoice}",
            media_list,
            ex=3600
        )

        # =========================
        # 🔥 UPDATE STATUS
        # =========================
        await execute(
            "UPDATE file_purchases SET status='paid' WHERE payment_id=$1",
            invoice
        )

        # =========================
        # 🔥 UPDATE BUY COUNT
        # =========================
        await execute(
            """
            UPDATE files
            SET buy_count = COALESCE(buy_count, 0) + 1
            WHERE code=$1
            """,
            purchase["file_code"]
        )

        # =========================
        # 🔥 DETEKSI VIP / VVIP
        # =========================
        code = purchase["file_code"].lower()

        if "vvip" in code:
            await send_upgrade_notif(call.bot, purchase["user_id"], "vvip")

        elif "vip" in code:
            await send_upgrade_notif(call.bot, purchase["user_id"], "vip")

        # =========================
        # 🔥 NOTIF CHANNEL
        # =========================
        try:
            masked_id = mask_user_id(purchase["user_id"])

            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🛒 Buy Now",
                            url="https://t.me/+T8c4gdEWf843ZWQ1"
                        )
                    ]
                ]
            )

            text = (
                "💸 <b>FILE PAYMENT SUCCESS</b>\n\n"
                f"📁 <b>Code:</b> <code>{purchase['file_code']}</code>\n"
                f"👤 <b>Buyer:</b> <code>{masked_id}</code>"
            )

            await call.bot.send_message(
                chat_id=NOTIF_CHANNEL_ID,
                text=text,
                parse_mode="HTML",
                reply_markup=kb
            )

        except Exception:
            logger.exception("NOTIF CHANNEL ERROR")

        # =========================
        # 🔥 HAPUS QR
        # =========================
        try:
            if purchase["qr_message_id"] and purchase["qr_chat_id"]:
                await call.bot.delete_message(
                    purchase["qr_chat_id"],
                    purchase["qr_message_id"]
                )
        except Exception:
            logger.exception("DELETE QR ERROR")

        # =========================
        # 🔥 KIRIM MENU MEDIA
        # =========================
        total = len(media_list)

        await call.message.answer(
            f"""
🎉 <b>Pembayaran berhasil</b>

📦 Total Media:
{total} file

Silahkan pilih:
""",
            parse_mode="HTML",
            reply_markup=media_keyboard(invoice, 1, total)
        )

    except Exception as e:
        logger.exception("CHECK PAYMENT ERROR %s", e)

        await call.message.answer(
            "❌ Terjadi error saat proses pembayaran"
        )

    finally:
        CHECK_LOCK.discard(invoice)



@router.callback_query(F.data.startswith("cancel:"))
async def cancel_payment(call: CallbackQuery):

    invoice = call.data.split(":")[1]


    await call.answer(
        "❌ Membatalkan..."
    )


    payment = await fetchrow(
        """
        SELECT *
        FROM file_purchases
        WHERE payment_id=$1
        """,
        invoice
    )


    if not payment:

        return await call.answer(
            "Data tidak ditemukan",
            show_alert=True
        )


    if payment["status"] == "paid":

        return await call.answer(
            "Sudah dibayar",
            show_alert=True
        )


    try:

        result = await BayarGG.cancel_payment(
            invoice
        )

        logger.info(
            "CANCEL RESULT %s",
            result
        )


    except Exception:

        logger.exception(
            "CANCEL ERROR"
        )



    await execute(
        """
        UPDATE file_purchases
        SET status='cancel'
        WHERE payment_id=$1
        """,
        invoice
    )


    try:

        await safe_delete(
            f"invoice:{invoice}"
        )

    except:
        pass



    try:

        if payment["qr_message_id"]:

            await call.bot.delete_message(
                payment["qr_chat_id"],
                payment["qr_message_id"]
            )


    except:

        pass



    await call.message.answer(
        "❌ <b>Pembayaran dibatalkan</b>",
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("mpage:"))
async def media_page(call: CallbackQuery):

    _, invoice, page = call.data.split(":")
    page = int(page)

    data = await safe_get(f"paidmedia:{invoice}")

    if not data:
        return await call.answer(
            "Session habis",
            show_alert=True
        )

    try:
        if isinstance(data, str):
            media_list = json.loads(data)
        else:
            media_list = data
    except Exception as e:
        logger.error(f"MEDIA PAGE JSON ERROR: {e}")
        return await call.answer(
            "❌ Data rusak",
            show_alert=True
        )

    await call.message.edit_reply_markup(
        reply_markup=media_keyboard(
            invoice,
            page,
            len(media_list)
        )
    )

    await call.answer()

@router.callback_query(F.data.startswith("sendpage:"))
async def send_page(call: CallbackQuery):

    try:
        _, invoice, page = call.data.split(":")
        page = int(page)

    except Exception:
        return await call.answer(
            "❌ Data halaman rusak",
            show_alert=True
        )


    data = await safe_get(
        f"paidmedia:{invoice}"
    )


    if not data:
        return await call.answer(
            "❌ Session habis",
            show_alert=True
        )


    try:
        if isinstance(data, str):
            media_list = json.loads(data)
        else:
            media_list = data

    except Exception as e:
        logger.error(
            f"MEDIA JSON ERROR {e}"
        )

        return await call.answer(
            "❌ Data media rusak",
            show_alert=True
        )


    # FILTER MEDIA VALID
    media_list = [
        m for m in media_list
        if isinstance(m, dict)
        and m.get("file_id")
    ]


    total = len(media_list)


    if total == 0:
        return await call.answer(
            "❌ Media kosong",
            show_alert=True
        )


    max_page = (
        total + PER_PAGE - 1
    ) // PER_PAGE


    page = max(
        1,
        min(page, max_page)
    )


    start = (
        page - 1
    ) * PER_PAGE


    end = start + PER_PAGE


    items = media_list[start:end]


    album = []


    for index,item in enumerate(items):

        file_id = item.get(
            "file_id"
        )

        if not file_id:
            continue


        media_type = (
            item.get("type")
            or "document"
        ).lower()


        caption = None


        if index == 0:
            caption = (
                "📦 <b>FILE BERHASIL DIBUKA</b>\n\n"
                f"📄 Halaman: {page}/{max_page}\n"
                f"📊 Total: {total} file"
            )


        try:

            if media_type == "photo":

                album.append(
                    InputMediaPhoto(
                        media=file_id,
                        caption=caption,
                        parse_mode="HTML"
                    )
                )


            elif media_type == "video":

                album.append(
                    InputMediaVideo(
                        media=file_id,
                        caption=caption,
                        parse_mode="HTML"
                    )
                )


            else:

                album.append(
                    InputMediaDocument(
                        media=file_id,
                        caption=caption,
                        parse_mode="HTML"
                    )
                )


        except Exception as e:

            logger.error(
                f"BUILD ALBUM ERROR {e}"
            )



    if not album:
        return await call.answer(
            "❌ Album kosong",
            show_alert=True
        )


    try:

        if len(album) == 1:

            await call.bot.send_document(
                chat_id=call.message.chat.id,
                document=album[0].media,
                protect_content=True
            )

        else:

            await call.bot.send_media_group(
                chat_id=call.message.chat.id,
                media=album,
                protect_content=True
            )


    except Exception as e:

        logger.exception(
            f"SEND ALBUM ERROR {e}"
        )

        return await call.answer(
            "❌ Gagal kirim media",
            show_alert=True
        )



    await call.message.answer(
        f"📦 Halaman {page}/{max_page}\n"
        f"✅ {len(album)} media terkirim",
        reply_markup=media_keyboard(
            invoice,
            page,
            total
        )
    )


    await call.answer()
    
@router.callback_query(F.data.startswith("sendall:"))
async def send_all(call: CallbackQuery):

    invoice = call.data.split(":")[1]

    data = await safe_get(f"paidmedia:{invoice}")

    if not data:
        return await call.answer(
            "Session habis",
            show_alert=True
        )

    try:
        if isinstance(data, str):
            media_list = json.loads(data)
        else:
            media_list = data
    except Exception as e:
        logger.error(f"SEND ALL JSON ERROR: {e}")
        return await call.answer(
            "❌ Data rusak",
            show_alert=True
        )

    media_list = [
        m for m in media_list
        if isinstance(m, dict) and m.get("message_id")
    ]

    if not media_list:
        return await call.answer(
            "❌ Media kosong",
            show_alert=True
        )

    status = await call.message.answer(
        f"📦 Mengirim {len(media_list)} file..."
    )

    sukses = 0
    gagal = 0

    for i, item in enumerate(media_list, start=1):
        try:
            msg_id = int(item["message_id"])

            await call.bot.copy_message(
                chat_id=call.message.chat.id,
                from_chat_id=STORAGE_CHANNEL_ID,
                message_id=msg_id,
                protect_content=True
            )

            sukses += 1

            if i % 10 == 0:
                try:
                    await status.edit_text(
                        f"📦 Mengirim...\n{sukses}/{len(media_list)}"
                    )
                except Exception:
                    pass

            await asyncio.sleep(0.3)

        except Exception as e:
            gagal += 1
            logger.exception(f"SEND ALL ERROR: {e}")

    await status.edit_text(
        f"✅ Selesai\n\n"
        f"📦 Berhasil: {sukses}\n"
        f"❌ Gagal: {gagal}"
    )

    await call.answer()
