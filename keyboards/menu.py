from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from utils.user_lang import get_user_language


async def home_kb(user_id):

    lang = await get_user_language(user_id)


    if lang == "id":

        return InlineKeyboardMarkup(
            inline_keyboard=[

                [
                    InlineKeyboardButton(
                        text="📤 Upload File",
                        callback_data="upfile"
                    ),
                    InlineKeyboardButton(
                        text="📥 Ambil File",
                        callback_data="getfile"
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="🏆 File Teratas",
                        callback_data="top_file"
                    ),
                    InlineKeyboardButton(
                        text="🆕 Kode Baru",
                        callback_data="new_code"
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="🔎 Cari Kode",
                        callback_data="search_code"
                    ),
                    InlineKeyboardButton(
                        text="💰 Cari Harga",
                        callback_data="search_price"
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="👤 Akun",
                        callback_data="account"
                    ),
                    InlineKeyboardButton(
                        text="💎 VVIP",
                        callback_data="vvip"
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="💸 Tarik Saldo",
                        callback_data="withdraw"
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="ℹ️ Bantuan",
                        callback_data="help"
                    )
                ]

            ]
        )


    else:

        return InlineKeyboardMarkup(
            inline_keyboard=[

                [
                    InlineKeyboardButton(
                        text="📤 Upload File",
                        callback_data="upfile"
                    ),
                    InlineKeyboardButton(
                        text="📥 Get File",
                        callback_data="getfile"
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="🏆 Top File",
                        callback_data="top_file"
                    ),
                    InlineKeyboardButton(
                        text="🆕 New Code",
                        callback_data="new_code"
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="🔎 Search Code",
                        callback_data="search_code"
                    ),
                    InlineKeyboardButton(
                        text="💰 Search Price",
                        callback_data="search_price"
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="👤 Account",
                        callback_data="account"
                    ),
                    InlineKeyboardButton(
                        text="💎 VVIP",
                        callback_data="vvip"
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="💸 Withdraw",
                        callback_data="withdraw"
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="ℹ️ Help",
                        callback_data="help"
                    )
                ]

            ]
        )
