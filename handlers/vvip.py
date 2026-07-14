import qrcode
from io import BytesIO
from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import get_pool
from utils.bayargg import BayarGG
from config_vip import VIP_PACKAGES


router = Router()


# =========================
# VIP MENU
# =========================
@router.callback_query(F.data == "vvip")
async def vvip_menu(call: CallbackQuery):

    kb = InlineKeyboardBuilder()

    for key, paket in VIP_PACKAGES.items():
        kb.button(
            text=f"💎 {paket['name']} • Rp {paket['price']:,}".replace(",", "."),
            callback_data=f"buyvip:{key}"
        )

    kb.button(
        text="🔙 Kembali",
        callback_data="account"
    )

    kb.adjust(1)

    text = (
        "<b><i>💎 VVIP PREMIUM ACCESS</i></b>\n"
        "━━━━━━━━━━━━━━\n\n"
        "<b><i>Nikmati semua fitur premium selama VIP aktif.</i></b>\n\n"
        "<b><i>✨ BENEFIT VIP</i></b>\n"
        "• 🚀 <b><i>Otomatis Open File Paid</i></b>\n"
        "• ⚡ <b><i>Priority Download</i></b>\n"
        "• 📂 <b><i>Unlimited File Access</i></b>\n"
        "• 🎁 <b><i>Akses File Premium</i></b>\n"
        "• 🔥 <b><i>Update Tercepat</i></b>\n"
        "• 💬 <b><i>Priority Support</i></b>\n"
        "• 🛡 <b><i>Masa Aktif Sesuai Paket</i></b>\n\n"
        "━━━━━━━━━━━━━━\n"
        "<b><i>👇 Pilih Paket VIP:</i></b>"
    )

    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )

    await call.answer()


# =========================
# BUY VIP
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
        "<b><i>⏳ Membuat invoice pembayaran...</i></b>",
        parse_mode="HTML"
    )

    try:
        payment = await BayarGG.create_payment(
            amount=paket["price"],
            description=paket["name"],
            payment_url="https://www.bayar.gg/pay",
            callback_url=(
                "https://earnfilebot-production.up.railway.app"
                "/bayargg/webhook"
            ),
            customer_name=call.from_user.full_name,
            payment_method="qris"
        )

    except Exception as e:
        return await call.message.edit_text(
            f"<b><i>❌ Gagal membuat invoice</i></b>\n\n"
            f"<code>{e}</code>",
            parse_mode="HTML"
        )

    if not payment:
        return await call.message.edit_text(
            "<b><i>❌ Invoice gagal dibuat.</i></b>",
            parse_mode="HTML"
        )

    invoice_id = payment["invoice_id"]
    payment_url = payment.get("payment_url")
    qr_string = payment.get("qris_string")

    expires_at = None

    if payment.get("expires_at"):
        try:
            expires_at = datetime.fromisoformat(
                payment["expires_at"]
            )
        except:
            pass

    pool = await get_pool()

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
                'vip'
            )
            """,
            call.from_user.id,
            paket_id,
            invoice_id,
            paket["price"],
            invoice_id,
            payment_url,
            expires_at
        )

    except Exception as e:
        return await call.message.edit_text(
            f"<b><i>❌ Database Error</i></b>\n\n"
            f"<code>{e}</code>",
            parse_mode="HTML"
        )

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


    text = (
        "<b><i>💎 INVOICE VIP BERHASIL DIBUAT</i></b>\n"
        "━━━━━━━━━━━━━━\n\n"
        f"📦 <b><i>Paket :</i></b> {paket['name']}\n"
        f"💰 <b><i>Harga :</i></b> Rp {paket['price']:,}\n"
        f"🧾 <b><i>Invoice :</i></b>\n"
        f"<code>{invoice_id}</code>\n\n"
        "⏳ <b><i>Status : MENUNGGU PEMBAYARAN</i></b>\n\n"
        "<b><i>Silakan scan QRIS di bawah.</i></b>\n"
        "<b><i>VIP akan aktif otomatis setelah pembayaran berhasil.</i></b>"
    ).replace(",", ".")


    qr = qrcode.make(qr_string)

    buf = BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)


    await call.message.answer_photo(
        BufferedInputFile(
            buf.getvalue(),
            filename="vip_qris.png"
        ),
        caption=text,
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )

    await call.answer()


# =========================
# WAITING PAYMENT
# =========================
@router.callback_query(F.data == "waiting_payment")
async def waiting_payment(call: CallbackQuery):

    await call.answer(
        "⏳ Pembayaran diproses otomatis setelah berhasil.",
        show_alert=True
    )
