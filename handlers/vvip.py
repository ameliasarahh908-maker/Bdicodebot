import qrcode

from io import BytesIO
from datetime import datetime

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    BufferedInputFile
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


from database import get_pool
from utils.bayargg import BayarGG
from config_vip import VIP_PACKAGES


router = Router()



# =========================
# VIP / VVIP MENU
# =========================
@router.callback_query(F.data == "vvip")
async def vvip_menu(call: CallbackQuery):

    kb = InlineKeyboardBuilder()


    for key, paket in VIP_PACKAGES.items():

        kb.button(
            text=(
                f"💎 {paket['name']} • "
                f"Rp {paket['price']:,}"
            ).replace(",", "."),

            callback_data=f"buyvip:{key}"
        )


    kb.button(
        text="🔙 Kembali",
        callback_data="account"
    )


    kb.adjust(1)


    text = (
        "<b><i>💎 PREMIUM ACCESS</i></b>\n"
        "━━━━━━━━━━━━━━\n\n"

        "Pilih paket premium:\n\n"

        "💠 <b>VIP</b>\n"
        "• Akses file premium\n"
        "• Masa aktif sesuai paket\n"
        "• Tidak bisa upload\n\n"

        "💎 <b>VVIP</b>\n"
        "• Semua fitur VIP\n"
        "• Bisa upload file\n"
        "• Storage uploader\n\n"

        "━━━━━━━━━━━━━━\n"
        "👇 Pilih paket:"
    )


    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )


    await call.answer()





# =========================
# BUY VIP / VVIP
# =========================
@router.callback_query(F.data.startswith("buyvip:"))
async def buy_vip(call: CallbackQuery):


    paket_id = call.data.split(":")[1]


    if paket_id not in VIP_PACKAGES:

        return await call.answer(
            "❌ Paket tidak ditemukan",
            show_alert=True
        )



    paket = VIP_PACKAGES[paket_id]



    await call.message.edit_text(
        "⏳ Membuat invoice pembayaran...",
        parse_mode="HTML"
    )



    # =========================
    # CREATE PAYMENT
    # =========================
    try:

        payment = await BayarGG.create_payment(

            amount=paket["price"],

            description=paket["name"],

            payment_url="https://www.bayar.gg/pay",

            callback_url=(
                "https://worker-production-87c6.up.railway.app"
                "/bayargg/webhook"
            ),

            customer_name=call.from_user.full_name,

            payment_method="qris"
        )


    except Exception as e:


        return await call.message.edit_text(

            "❌ <b>Gagal membuat invoice</b>\n\n"
            f"<code>{e}</code>",

            parse_mode="HTML"
        )



    if not payment:

        return await call.message.edit_text(

            "❌ Invoice gagal dibuat.",

            parse_mode="HTML"
        )



    invoice_id = payment["invoice_id"]


    payment_url = payment.get(
        "payment_url"
    )


    qr_string = payment.get(
        "qris_string"
    )


    expires_at = None



    if payment.get("expires_at"):

        try:

            expires_at = datetime.fromisoformat(
                payment["expires_at"]
            )

        except:

            pass




    pool = await get_pool()



    # =========================
    # SAVE PAYMENT
    # =========================
    try:


        await pool.execute(

            """
            INSERT INTO payments
            (
                user_id,
                code,
                reference,
                amount,
                status,
                provider,
                invoice_id,
                payment_url,
                expires_at,
                type
            )

            VALUES
            (
                $1,$2,$3,$4,
                'pending',
                'bayargg',
                $5,$6,$7,
                $8
            )
            """,

            call.from_user.id,

            paket_id,

            invoice_id,

            paket["price"],

            invoice_id,

            payment_url,

            expires_at,

            paket.get(
                "type",
                "vip"
            )

        )


    except Exception as e:


        return await call.message.edit_text(

            "❌ <b>Database Error</b>\n\n"
            f"<code>{e}</code>",

            parse_mode="HTML"
        )




    paket_type = paket.get(
        "type",
        "vip"
    )



    if paket_type == "vvip":

        akses = (
            "💎 VVIP\n"
            "✅ Bisa upload file\n"
            "✅ Akses premium"
        )

    else:

        akses = (
            "💠 VIP\n"
            "✅ Akses premium\n"
            "❌ Tidak bisa upload"
        )




    text = (

        "<b><i>💎 INVOICE BERHASIL</i></b>\n"
        "━━━━━━━━━━━━━━\n\n"

        f"📦 Paket : <b>{paket['name']}</b>\n"

        f"💰 Harga : <b>Rp "
        f"{paket['price']:,}</b>\n\n"

        f"{akses}\n\n"

        "🧾 Invoice:\n"

        f"<code>{invoice_id}</code>\n\n"

        "⏳ Status: MENUNGGU PEMBAYARAN\n\n"

        "Scan QRIS di bawah.\n"

        "Aktif otomatis setelah pembayaran berhasil."

    ).replace(",", ".")



    kb = InlineKeyboardBuilder()


    kb.button(
        text="⏳ Menunggu Pembayaran",
        callback_data="waiting_payment"
    )


    kb.button(
        text="🔙 Kembali",
        callback_data="vvip"
    )


    kb.adjust(1)



    # =========================
    # QR IMAGE
    # =========================
    if qr_string:


        qr = qrcode.make(
            qr_string
        )


        buf = BytesIO()


        qr.save(
            buf,
            format="PNG"
        )


        buf.seek(0)



        await call.message.answer_photo(

            BufferedInputFile(

                buf.getvalue(),

                filename="qris.png"

            ),

            caption=text,

            parse_mode="HTML",

            reply_markup=kb.as_markup()

        )


    else:


        await call.message.answer(

            text,

            parse_mode="HTML",

            reply_markup=kb.as_markup()

        )



    await call.answer()





# =========================
# WAITING PAYMENT
# =========================
@router.callback_query(
    F.data == "waiting_payment"
)
async def waiting_payment(
    call: CallbackQuery
):

    await call.answer(

        "⏳ Pembayaran akan dicek otomatis.",

        show_alert=True

    )
