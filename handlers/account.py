from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from database import get_pool

router = Router()

BOT_USERNAME = "Zyxfidzbot"  # 🔥 ganti ini


async def open_account(target, user_id):

    pool = await get_pool()

    user = await pool.fetchrow(
        """
        SELECT vip, vip_until, referral_count
        FROM users
        WHERE user_id=$1
        """,
        user_id
    )

    # =========================
    # REFERRAL
    # =========================
    referral_count = user["referral_count"] if user else 0
    ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"

    # =========================
    # VIP STATUS
    # =========================
    vip_status = "🆓 FREE"
    vip_type = "-"
    remaining = "-"
    duration = "-"

    if user and user["vip"] and user["vip_until"]:

        now = datetime.now(timezone.utc)
        vip_until = user["vip_until"]

        if vip_until.tzinfo is None:
            vip_until = vip_until.replace(tzinfo=timezone.utc)
        else:
            vip_until = vip_until.astimezone(timezone.utc)

        if vip_until > now:

            delta = vip_until - now
            remaining_days = max(1, delta.days)

            vip_status = "👑 VIP ACTIVE"

            if remaining_days <= 1:
                vip_type = "Harian"
            elif remaining_days <= 30:
                vip_type = "Bulanan"
            else:
                vip_type = "Lifetime"

            remaining = f"{remaining_days} hari"
            duration = f"{remaining_days} hari"

        else:
            # 🔥 AUTO DOWNGRADE
            await pool.execute(
                "UPDATE users SET vip=false, vip_until=NULL WHERE user_id=$1",
                user_id
            )

            vip_status = "❌ EXPIRED"
            remaining = "0 hari"
            duration = "0 hari"

    # =========================
    # TEXT UI
    # =========================
    text = (
        "━━━━━━━━━━━━━━\n"
        "👤 <b>ACCOUNT INFO</b>\n"
        "━━━━━━━━━━━━━━\n\n"
        f"🆔 User ID : <code>{user_id}</code>\n"
        f"💎 Status : {vip_status}\n"
        f"📦 Tipe : {vip_type}\n"
        f"⏳ Sisa VIP : {remaining}\n\n"

        "🎯 <b>REFERRAL</b>\n"
        f"👥 Total Undangan : <b>{referral_count}</b>\n"
        f"🔗 Link Kamu:\n"
        f"<code>{ref_link}</code>\n\n"

        "━━━━━━━━━━━━━━\n"
        "🚀 Ajak teman & dapat reward!"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💎 Upgrade VIP", callback_data="vip")],
            [InlineKeyboardButton(text="🔙 Kembali", callback_data="home")]
        ]
    )

    if isinstance(target, Message):
        await target.answer(
            text,
            parse_mode="HTML",
            reply_markup=kb
        )
    else:
        await target.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=kb
        )


@router.callback_query(F.data == "account")
async def account_handler(call: CallbackQuery):
    await open_account(call.message, call.from_user.id)
    await call.answer()


@router.message(F.text.in_(["👤 Akun", "👤 Account"]))
async def account(message: Message):
    await open_account(message, message.from_user.id)
