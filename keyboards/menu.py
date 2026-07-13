from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def home_kb():

    return ReplyKeyboardMarkup(
        keyboard=[

            [
                KeyboardButton(text="🔎 Search Code"),
                KeyboardButton(text="🏆 Top Code")
            ],

            [
                KeyboardButton(text="💰 Search Harga"),
                KeyboardButton(text="💎 VIP / VVIP")
            ]

        ],
        resize_keyboard=True
    )
