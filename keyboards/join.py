from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

def join_kb(bot_username: str, user_id: int):

    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="📢 Join Channel 1",
                    url="https://t.me/+T4sXrm9HtH9kZmE1"
                )
            ],

            [
                InlineKeyboardButton(
                    text="📢 Join Channel 2",
                    url="https://t.me/+0ddS3Ha4c2pkNmJl"
                )
            ],

            [
                InlineKeyboardButton(
                    text="📤 Bagikan Referral",
                    url=f"https://t.me/share/url?url={ref_link}"
                )
            ],

            [
                InlineKeyboardButton(
                    text="✅ Saya Sudah Join",
                    callback_data="check_join"
                )
            ],

        ]
    )
