from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from database import get_pool

router = Router()

BOT_USERNAME = "ZyxFidxBot"


def make_bar(current, target):

    percent = current / target

    filled = int(percent * 10)

    if filled > 10:
        filled = 10

    return "█" * filled + "░" * (10-filled)


@router.callback_query(F.data == "reward")
async def reward_menu(call: CallbackQuery):

    pool = await get_pool()

    user = await pool.fetchrow(
        """
        SELECT
            referral_count,
            ref_10_claimed,
            ref_20_claimed,
            ref_50_claimed
        FROM users
        WHERE chat_id=$1
        """,
        call.from_user.id
    )


    if not user:
        return await call.answer(
            "User tidak ditemukan",
            show_alert=True
        )


    count = user["referral_count"] or 0


    # TARGET BERIKUTNYA
    if count < 10:
        target = 10
        reward = "💠 VIP 1 Hari"

    elif count < 20:
        target = 20
        reward = "💠 VIP 5 Hari"

    elif count < 50:
        target = 50
        reward = "💎 VVIP 7 Hari"

    else:
        target = 50
        reward = "🎉 Semua reward selesai"


    bar = make_bar(
        count if count < target else target,
        target
    )


    link = (
        f"https://t.me/{BOT_USERNAME}"
        f"?start=ref_{call.from_user.id}"
    )


    text = (
        "🎁 <b>REFERRAL REWARD</b>\n\n"
        f"👥 Total Referral: <b>{count}</b>\n\n"
        f"{bar} {min(count,target)}/{target}\n\n"
        f"🎯 Target Berikutnya:\n"
        f"{reward}\n\n"
        "🔗 Link Referral Kamu:\n"
        f"<code>{link}</code>"
    )


    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔗 Bagikan Link",
                    url=link
                )
            ]
        ]
    )


    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb
    )

    await call.answer()
