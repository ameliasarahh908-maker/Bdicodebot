import asyncio
import qrcode
import logging

from io import BytesIO

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



# =================================================
# PAY FILE
# =================================================

@router.callback_query(F.data.startswith("pay:"))
async def pay_file(call: CallbackQuery):

    user_id = call.from_user.id
    code = call.data.split(":")[1]

    logger.info(
        "🔥 PAY START user=%s file=%s",
        user_id,
        code
    )

    await call.answer(
        "⏳ Membuat pembayaran..."
    )


    loading = None

    try:
        loading = await call.message.answer(
            "⏳ <b>Membuat QRIS...</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass


    async def fail(text):

        logger.warning(
            "PAY FAIL : %s",
            text
        )

        try:
            if loading:
                await loading.delete()
        except:
            pass

        await call.answer(
            text,
            show_alert=True
        )


    lock_key = f"paylock:{user_id}:{code}"


    try:

        lock = await safe_set(
            lock_key,
            "1",
            ex=PAY_LOCK_TTL,
            nx=True
        )

    except:

        lock = True


    if not lock:
        return await fail(
            "⏳ Tunggu sebentar"
        )



    try:

        # =========================
        # GET FILE
        # =========================

        logger.info("📦 GET FILE")


        file = await fetchrow(
            """
            SELECT *
            FROM files
            WHERE code=$1
            """,
            code
        )


        logger.info(
            "FILE RESULT %s",
            file
        )


        if not file:
            return await fail(
                "❌ File tidak ditemukan"
            )


        if not file["is_paid"]:
            return await fail(
                "File gratis"
            )


        if file["owner_id"] == user_id:
            return await fail(
                "Owner tidak perlu bayar"
            )


        price = file["price"] or 0


        # =========================
        # CHECK OLD PAYMENT
        # =========================


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


        logger.info(
            "OLD PAYMENT %s",
            old
        )


        if old:


            if old["status"]=="paid":

                return await fail(
                    "✅ File sudah dibeli"
                )


            if old["status"]=="pending":


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
                    f"""
⚠️ <b>Pembayaran masih pending</b>

🧾 Invoice:
<code>{invoice}</code>

Selesaikan pembayaran atau batalkan.
""",
                    parse_mode="HTML",
                    reply_markup=kb
                )


                return



        # =========================
        # CREATE BAYARGG
        # =========================


        logger.info(
            "CREATE PAYMENT"
        )


        data = await BayarGG.create_payment(
            amount=price,
            description=f"File {code}",
            customer_name=call.from_user.full_name
        )


        logger.info(
            "BAYARGG RESULT %s",
            data
        )



        invoice = (
            data.get("invoice_id")
            or data.get("invoice")
            or data.get("id")
        )


        qr_string = (
            data.get("qris_string")
            or data.get("qr_string")
            or data.get("qr")
        )


        amount = (
            data.get("amount")
            or price
        )



        if not invoice or not qr_string:

            return await fail(
                "❌ QRIS gagal dibuat"
            )



        # =========================
        # SAVE PAYMENT
        # =========================


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



        # =========================
        # QR IMAGE
        # =========================


        qr = qrcode.make(
            qr_string
        )


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

            caption=f"""
💳 <b>PAYMENT QRIS</b>

🧾 Invoice:
<code>{invoice}</code>

💰 Total:
Rp {amount:,}

Scan QR untuk membayar.
""".replace(",", "."),

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



        logger.info(
            "QR SENT %s",
            invoice
        )


    except Exception:

        logger.exception(
            "PAY ERROR"
        )

        await call.answer(
            "❌ Error pembayaran",
            show_alert=True
        )


    finally:

        try:

            if loading:
                await loading.delete()

        except:
            pass


        try:

            await safe_delete(
                lock_key
            )

        except:
            pass







# =================================================
# CHECK PAYMENT + SEND FILE
# =================================================


@router.callback_query(F.data.startswith("check:"))
async def check_payment(call: CallbackQuery):


    invoice = call.data.split(":")[1]


    await call.answer(
        "🔄 Mengecek..."
    )


    logger.info(
        "CHECK PAYMENT %s",
        invoice
    )



    result = await BayarGG.check_payment(
        invoice
    )


    logger.info(
        "CHECK RESULT %s",
        result
    )



    if not result:

        return await call.answer(
            "❌ Gagal cek",
            show_alert=True
        )



    status = (
        result.get("status")
        or
        result.get("payment_status")
    )



    if status != "paid":

        return await call.answer(
            "⏳ Belum dibayar",
            show_alert=True
        )



    purchase = await fetchrow(
        """
        SELECT *
        FROM file_purchases
        WHERE payment_id=$1
        """,
        invoice
    )



    if not purchase:

        return await call.message.answer(
            "❌ Data pembelian hilang"
        )



    await execute(
        """
        UPDATE file_purchases
        SET status='paid'
        WHERE payment_id=$1
        """,
        invoice
    )



    file = await fetchrow(
        """
        SELECT *
        FROM files
        WHERE code=$1
        """,
        purchase["file_code"]
    )



    logger.info(
        "SEND FILE DATA %s",
        file
    )



    if not file:

        return await call.message.answer(
            "❌ File tidak ditemukan"
        )



    try:


        ftype = file["file_type"]


        if ftype in [
            "photo",
            "image"
        ]:

            await call.message.answer_photo(
                file["file_id"]
            )


        elif ftype=="video":


            await call.message.answer_video(
                file["file_id"]
            )


        else:


            await call.message.answer_document(
                file["file_id"]
            )



        await call.message.answer(
            "✅ File berhasil dikirim"
        )



    except Exception:

        logger.exception(
            "SEND FILE ERROR"
        )

        await call.message.answer(
            "❌ Pembayaran sukses tapi file gagal dikirim, hubungi admin"
        )








# =================================================
# CANCEL PAYMENT
# =================================================


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



    if payment["status"]=="paid":

        return await call.answer(
            "Sudah dibayar",
            show_alert=True
        )



    # CANCEL BAYARGG

    try:

        result = await BayarGG.cancel_payment(
            invoice
        )


        logger.info(
            "BAYARGG CANCEL RESULT %s",
            result
        )


    except Exception:

        logger.exception(
            "BAYARGG CANCEL ERROR"
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


    except Exception:

        pass



    await call.message.answer(
        "❌ <b>Pembayaran dibatalkan</b>",
        parse_mode="HTML"
    )
