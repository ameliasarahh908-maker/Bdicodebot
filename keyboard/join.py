from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

def join_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 Join Channel",
                    url="https://t.me/+xeu7ym63WsE3YTZl"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥 Join Group",
                    url="https://t.me/+GZDnnCvYvo5lZmU8"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ CHECK",
                    callback_data="check_sub"
                )
            ]
        ]
    )
