from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


language_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🇮🇩 Indonesia",
                callback_data="setlang:id"
            )
        ],
        [
            InlineKeyboardButton(
                text="🇬🇧 English",
                callback_data="setlang:en"
            )
        ]
    ]
)
