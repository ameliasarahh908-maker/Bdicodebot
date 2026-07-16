from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils.user_lang import get_user_language


async def home_kb(user_id):

    lang = await get_user_language(user_id)

    if lang == "id":
        store = "🏪 Store"
        top = "🏆 Top 10 Code"
        account = "👤 Akun"
        upgrade = "💎 Upgrade"
    else:
        store = "🏪 Store"
        top = "🏆 Top 10 Code"
        account = "👤 Account"
        upgrade = "💎 Upgrade"


    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=store),
                KeyboardButton(text=top)
            ],
            [
                KeyboardButton(text=account),
                KeyboardButton(text=upgrade)
            ]
        ],
        resize_keyboard=True
    )
