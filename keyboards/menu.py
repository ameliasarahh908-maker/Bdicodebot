from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.user_lang import get_user_language


async def home_kb(user_id):

    lang = await get_user_language(user_id)

    # =========================
    # TEXT
    # =========================
    if lang == "id":
        t = {
            "upload": "📤 Upload File",
            "get": "📥 Ambil File",
            "top": "🏆 File Teratas",
            "new": "🆕 Kode Baru",
            "search_code": "🔎 Cari Kode",
            "search_price": "💰 Cari Harga",
            "account": "👤 Akun",
            "vip": "💎 VIP",
            "help": "ℹ️ Bantuan"
        }
    else:
        t = {
            "upload": "📤 Upload File",
            "get": "📥 Get File",
            "top": "🏆 Top File",
            "new": "🆕 New Code",
            "search_code": "🔎 Search Code",
            "search_price": "💰 Search Price",
            "account": "👤 Account",
            "vip": "💎 VIP",
            "help": "ℹ️ Help"
        }

    # =========================
    # KEYBOARD
    # =========================
    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(text=t["upload"], callback_data="upfile"),
                InlineKeyboardButton(text=t["get"], callback_data="getfile")
            ],

            [
                InlineKeyboardButton(text=t["top"], callback_data="top_file"),
                InlineKeyboardButton(text=t["new"], callback_data="new_code")
            ],

            [
                InlineKeyboardButton(text=t["search_code"], callback_data="search_code"),
                InlineKeyboardButton(text=t["search_price"], callback_data="search_price")
            ],

            [
                InlineKeyboardButton(text=t["account"], callback_data="account"),
                InlineKeyboardButton(text=t["vip"], callback_data="vvip")
            ],

            [
                InlineKeyboardButton(text=t["help"], callback_data="help")
            ]

        ]
    )
