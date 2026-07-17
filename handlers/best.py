from math import ceil

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from database import get_pool


router = Router()


LIMIT = 10



async def show_best_seller(
    call: CallbackQuery,
    page: int = 1
):

    pool = await get_pool()


    total = await pool.fetchval(
        """
        SELECT COUNT(*)
        FROM files
        """
    )


    if total == 0:

        return await call.message.edit_text(
            "❌ Belum ada data.",
            reply_markup=back_keyboard()
        )



    max_page = ceil(
        total / LIMIT
    )


    page = max(
        1,
        min(
            page,
            max_page
        )
    )


    offset = (
        page - 1
    ) * LIMIT



    rows = await pool.fetch(
        """
        SELECT
            code,
            title,
            buy_count,
            price
        FROM files
        ORDER BY
            buy_count DESC,
            created_at DESC
        LIMIT $1
        OFFSET $2
        """,
        LIMIT,
        offset
    )



    text = (
        "📈 <b>CODE TERLARIS</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )



    for i, row in enumerate(
        rows,
        start=offset + 1
    ):


        harga = (
            "Gratis"
            if row["price"] == 0
            else f"Rp{row['price']:,}"
        )


        text += (
            f"{i}. 📌 <b>{row['title']}</b>\n"
            f"🔑 <code>{row['code']}</code>\n"
            f"🛒 Dibeli : <b>{row['buy_count']}</b>x\n"
            f"💰 Harga : {harga}\n\n"
        )



    keyboard = page_keyboard(
        page,
        max_page
    )



    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )


    await call.answer()



def page_keyboard(
    page,
    max_page
):

    buttons = []


    if page > 1:

        buttons.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=f"best:{page-1}"
            )
        )


    buttons.append(
        InlineKeyboardButton(
            text=f"{page}/{max_page}",
            callback_data="ignore"
        )
    )


    if page < max_page:

        buttons.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=f"best:{page+1}"
            )
        )


    return InlineKeyboardMarkup(
        inline_keyboard=[

            buttons,

            [
                InlineKeyboardButton(
                    text="🏪 Kembali Store",
                    callback_data="store"
                )
            ]

        ]
    )



def back_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏪 Store",
                    callback_data="store"
                )
            ]
        ]
    )



@router.callback_query(
    F.data == "store_best"
)
async def best_open(
    call: CallbackQuery
):

    await show_best_seller(
        call,
        1
    )



@router.callback_query(
    F.data.startswith("best:")
)
async def best_page(
    call: CallbackQuery
):

    page = int(
        call.data.split(":")[1]
    )


    await show_best_seller(
        call,
        page
    )



@router.callback_query(
    F.data == "ignore"
)
async def ignore(
    call: CallbackQuery
):

    await call.answer()
