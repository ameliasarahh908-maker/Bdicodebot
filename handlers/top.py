from math import ceil

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from database import get_pool
from aiogram.types import Message


router = Router()


LIMIT = 10



async def show_top_code(target: Message | CallbackQuery, page: int = 1):
    pool = await get_pool()

    if isinstance(target, CallbackQuery):
        msg = target.message
    else:
        msg = target

    total = await pool.fetchval("""
        SELECT COUNT(*)
        FROM files
    """)

    if total == 0:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏪 Store", callback_data="store")]
        ])
        if isinstance(target, CallbackQuery):
            await msg.edit_text("❌ Belum ada code.", reply_markup=keyboard)
            return await target.answer()
        return await msg.answer("❌ Belum ada code.", reply_markup=keyboard)

    max_page = ceil(total / LIMIT)
    page = max(1, min(page, max_page))
    offset = (page - 1) * LIMIT

    rows = await pool.fetch("""
        SELECT code,title,view_count
        FROM files
        ORDER BY view_count DESC,created_at DESC
        LIMIT $1 OFFSET $2
    """, LIMIT, offset)

    text = "🔥 <b>TOP CODE TERPOPULER</b>\n━━━━━━━━━━━━━━━━━━\n\n"

    for i, row in enumerate(rows, start=offset + 1):
        rank = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{rank} <b>{row['title']}</b>\n🔑 <code>{row['code']}</code>\n👁 Dibuka : <b>{row['view_count']}</b>x\n\n"

    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"top:{page-1}"))
    buttons.append(InlineKeyboardButton(text=f"{page}/{max_page}", callback_data="ignore"))
    if page < max_page:
        buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"top:{page+1}"))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        buttons,
        [InlineKeyboardButton(text="🏪 Kembali Store", callback_data="store")]
    ])

    if isinstance(target, CallbackQuery):
        await msg.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await target.answer()
    else:
        await msg.answer(text, parse_mode="HTML", reply_markup=keyboard)



@router.callback_query(
    F.data == "store_top"
)
async def top_open(
    call: CallbackQuery
):

    await show_top_code(
        call,
        1
    )



@router.callback_query(
    F.data.startswith("top:")
)
async def top_page(
    call: CallbackQuery
):

    page = int(
        call.data.split(":")[1]
    )


    await show_top_code(
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


# =========================
# PREMIUM
# =========================

async def show_premium(
    target,
    page: int = 1
):

    pool = await get_pool()


    total = await pool.fetchval(
        """
        SELECT COUNT(*)
        FROM files
        WHERE price > 0
        """
    )


    if total == 0:

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🏪 Store",
                        callback_data="store"
                    )
                ]
            ]
        )

        return await target.message.edit_text(
            "❌ Belum ada code premium.",
            parse_mode="HTML",
            reply_markup=keyboard
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
            price,
            buy_count
        FROM files
        WHERE price > 0
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
        "💎 <b>CODE PREMIUM</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )


    for i, row in enumerate(
        rows,
        start=offset + 1
    ):

        text += (
            f"{i}. 📌 <b>{row['title']}</b>\n"
            f"🔑 <code>{row['code']}</code>\n"
            f"💰 Harga : Rp{row['price']:,}\n"
            f"🛒 Dibeli : {row['buy_count']}x\n\n"
        )



    keyboard = page_keyboard(
        page,
        max_page,
        "store_premium"
    )


    await target.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )


    await target.answer()



@router.callback_query(
    F.data.startswith("store_premium")
)
async def store_premium(
    call: CallbackQuery
):

    page = 1


    if ":" in call.data:

        page = int(
            call.data.split(":")[1]
        )


    await show_premium(
        call,
        page
    )

# =========================
# TERLARIS
# =========================

async def show_best_seller(
    target,
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

        return await target.message.edit_text(
            "❌ Belum ada data.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🏪 Store",
                            callback_data="store"
                        )
                    ]
                ]
            )
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
            f"🛒 Dibeli : {row['buy_count']}x\n"
            f"💰 Harga : {harga}\n\n"
        )


    keyboard = page_keyboard(
        page,
        max_page,
        "store_best"
    )


    await target.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )


    await target.answer()



@router.callback_query(
    F.data.startswith("store_best")
)
async def store_best(
    call: CallbackQuery
):

    page = 1


    if ":" in call.data:

        page = int(
            call.data.split(":")[1]
        )


    await show_best_seller(
        call,
        page
    )

# =========================
# TERBARU
# =========================

async def show_new_files(
    target,
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

        return await target.message.edit_text(
            "❌ Belum ada data.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🏪 Store",
                            callback_data="store"
                        )
                    ]
                ]
            )
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
            price,
            created_at
        FROM files
        ORDER BY
            created_at DESC
        LIMIT $1
        OFFSET $2
        """,
        LIMIT,
        offset
    )



    text = (
        "🆕 <b>CODE TERBARU</b>\n"
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
            f"💰 Harga : {harga}\n\n"
        )


    keyboard = page_keyboard(
        page,
        max_page,
        "store_new"
    )


    await target.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )


    await target.answer()



@router.callback_query(
    F.data.startswith("store_new")
)
async def store_new(
    call: CallbackQuery
):

    page = 1


    if ":" in call.data:

        page = int(
            call.data.split(":")[1]
        )


    await show_new_files(
        call,
        page
    )



# =========================
# PAGINATION KEYBOARD
# =========================

def page_keyboard(
    page,
    max_page,
    prefix
):

    buttons = []


    if page > 1:

        buttons.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=f"{prefix}:{page-1}"
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
                callback_data=f"{prefix}:{page+1}"
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


async def top_command(
    message: Message
):

    await show_top_code(
        message,
        1
    )
