from math import ceil
import random

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from database import get_pool
from keyboards.store import store_keyboard


router = Router()

LIMIT = 10


# =========================
# STORE MENU
# =========================

async def store_command(message: Message):

    pool = await get_pool()

    total_code = await pool.fetchval(
        """
        SELECT COUNT(*)
        FROM files
        """
    )

    total_view = await pool.fetchval(
        """
        SELECT COALESCE(
            SUM(view_count),
            0
        )
        FROM files
        """
    )

    total_buy = await pool.fetchval(
        """
        SELECT COALESCE(
            SUM(buy_count),
            0
        )
        FROM files
        """
    )


    text = (
        "🏪 <b>STORE CLICKLINK</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "👋 Selamat datang di Store.\n\n"
        "Temukan berbagai code premium "
        "maupun gratis.\n\n"
        f"📦 Total Code : <b>{total_code:,}</b>\n"
        f"👁 Total Dibuka : <b>{total_view:,}</b>\n"
        f"🛒 Total Pembelian : <b>{total_buy:,}</b>\n\n"
        "Silakan pilih menu di bawah."
    )


    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=store_keyboard()
    )



# =========================
# BUTTON STORE
# =========================

@router.message(F.text == "🏪 Store")
async def store_menu(message: Message):

    await store_command(message)



@router.callback_query(F.data == "store")
async def store_callback(call: CallbackQuery):

    try:
        await call.message.delete()
    except:
        pass

    await store_command(
        call.message
    )

    await call.answer()


# =========================
# TOP CODE
# =========================

async def show_top_code(
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

        text = "❌ Belum ada code."

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

        if isinstance(target, Message):

            return await target.answer(
                text,
                reply_markup=keyboard
            )

        return await target.message.edit_text(
            text,
            reply_markup=keyboard
        )


    max_page = ceil(
        total / LIMIT
    )


    if page < 1:
        page = 1

    if page > max_page:
        page = max_page


    offset = (
        page - 1
    ) * LIMIT


    rows = await pool.fetch(
        """
        SELECT
            code,
            title,
            view_count,
            price
        FROM files
        ORDER BY
            view_count DESC,
            created_at DESC
        LIMIT $1
        OFFSET $2
        """,
        LIMIT,
        offset
    )


    text = (
        "🔥 <b>TOP CODE</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )


    for i, row in enumerate(
        rows,
        start=offset + 1
    ):

        price = (
            "Gratis"
            if row["price"] == 0
            else f"Rp{row['price']:,}"
        )


        text += (
            f"{i}. 📌 <b>{row['title']}</b>\n"
            f"🔑 <code>{row['code']}</code>\n"
            f"👁 Dibuka : {row['view_count']}x\n"
            f"💰 Harga : {price}\n\n"
        )



    nav = []


    if page > 1:

        nav.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=f"store_top:{page-1}"
            )
        )


    nav.append(
        InlineKeyboardButton(
            text=f"{page}/{max_page}",
            callback_data="ignore"
        )
    )


    if page < max_page:

        nav.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=f"store_top:{page+1}"
            )
        )



    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            nav,
            [
                InlineKeyboardButton(
                    text="🏪 Store",
                    callback_data="store"
                )
            ]
        ]
    )


    if isinstance(target, Message):

        await target.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

    else:

        await target.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )



@router.callback_query(
    F.data.startswith("store_top")
)
async def store_top(call: CallbackQuery):

    page = 1


    if ":" in call.data:

        page = int(
            call.data.split(":")[1]
        )


    await show_top_code(
        call,
        page
    )

    await call.answer()



@router.callback_query(
    F.data == "ignore"
)
async def ignore(call: CallbackQuery):

    await call.answer()


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

        return await target.answer(
            "❌ Belum ada data."
        )


    max_page = ceil(
        total / LIMIT
    )


    page = max(
        1,
        min(page, max_page)
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

        price = (
            "Gratis"
            if row["price"] == 0
            else f"Rp{row['price']:,}"
        )


        text += (
            f"{i}. 📌 <b>{row['title']}</b>\n"
            f"🔑 <code>{row['code']}</code>\n"
            f"🛒 Dibeli : {row['buy_count']}x\n"
            f"💰 Harga : {price}\n\n"
        )


    keyboard = page_keyboard(
        page,
        max_page,
        "store_best",
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
async def store_best(call: CallbackQuery):

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


    max_page = ceil(
        total / LIMIT
    )


    page = max(
        1,
        min(page, max_page)
    )


    offset = (
        page - 1
    ) * LIMIT



    rows = await pool.fetch(
        """
        SELECT
            code,
            title,
            created_at,
            price
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

        price = (
            "Gratis"
            if row["price"] == 0
            else f"Rp{row['price']:,}"
        )


        text += (
            f"{i}. 📌 <b>{row['title']}</b>\n"
            f"🔑 <code>{row['code']}</code>\n"
            f"💰 {price}\n\n"
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
async def store_new(call: CallbackQuery):

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
        return await target.answer(
            "❌ Belum ada code premium."
        )


    max_page = ceil(
        total / LIMIT
    )

    page = max(
        1,
        min(page, max_page)
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
            buy_count DESC
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
            f"💰 Rp{row['price']:,}\n"
            f"🛒 {row['buy_count']}x dibeli\n\n"
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
async def store_premium(call: CallbackQuery):

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
# GRATIS
# =========================

@router.callback_query(
    F.data == "store_free"
)
async def store_free(call: CallbackQuery):

    pool = await get_pool()

    rows = await pool.fetch(
        """
        SELECT
            code,
            title
        FROM files
        WHERE price = 0
        ORDER BY
            created_at DESC
        LIMIT 10
        """
    )


    if not rows:

        return await call.answer(
            "Tidak ada code gratis.",
            show_alert=True
        )


    text = (
        "🆓 <b>CODE GRATIS</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )


    for i, row in enumerate(
        rows,
        start=1
    ):

        text += (
            f"{i}. 📌 <b>{row['title']}</b>\n"
            f"🔑 <code>{row['code']}</code>\n\n"
        )


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


    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )

    await call.answer()



# =========================
# FAVORIT
# =========================

@router.callback_query(
    F.data == "store_favorite"
)
async def store_favorite(call: CallbackQuery):

    pool = await get_pool()


    rows = await pool.fetch(
        """
        SELECT
            code,
            title,
            favorite_count
        FROM files
        ORDER BY
            favorite_count DESC
        LIMIT 10
        """
    )


    text = (
        "❤️ <b>FAVORIT</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )


    for i, row in enumerate(
        rows,
        start=1
    ):

        text += (
            f"{i}. 📌 <b>{row['title']}</b>\n"
            f"🔑 <code>{row['code']}</code>\n"
            f"❤️ {row['favorite_count']} favorit\n\n"
        )


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


    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )

    await call.answer()



# =========================
# RANDOM
# =========================

@router.callback_query(
    F.data == "store_random"
)
async def store_random(call: CallbackQuery):

    pool = await get_pool()


    rows = await pool.fetch(
        """
        SELECT
            code,
            title,
            price
        FROM files
        ORDER BY RANDOM()
        LIMIT 10
        """
    )


    text = (
        "🎲 <b>RANDOM CODE</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )


    for i, row in enumerate(
        rows,
        start=1
    ):

        text += (
            f"{i}. 📌 <b>{row['title']}</b>\n"
            f"🔑 <code>{row['code']}</code>\n\n"
        )


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


    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )

    await call.answer()


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
                    text="🏪 Store",
                    callback_data="store"
                )
            ]
        ]
    )



# =========================
# KATEGORI
# =========================

@router.callback_query(
    F.data == "store_category"
)
async def store_category(call: CallbackQuery):

    pool = await get_pool()


    rows = await pool.fetch(
        """
        SELECT
            category,
            COUNT(*) AS total
        FROM files
        WHERE category IS NOT NULL
        GROUP BY category
        ORDER BY total DESC
        """
    )


    if not rows:

        return await call.answer(
            "Kategori kosong.",
            show_alert=True
        )


    keyboard = []


    for row in rows:

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"📂 {row['category']} ({row['total']})",
                    callback_data=f"category:{row['category']}"
                )
            ]
        )


    keyboard.append(
        [
            InlineKeyboardButton(
                text="🏪 Store",
                callback_data="store"
            )
        ]
    )


    await call.message.edit_text(
        "📂 <b>PILIH KATEGORI</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard
        )
    )

    await call.answer()



@router.callback_query(
    F.data.startswith("category:")
)
async def category_files(call: CallbackQuery):

    category = call.data.split(":")[1]


    pool = await get_pool()


    rows = await pool.fetch(
        """
        SELECT
            code,
            title
        FROM files
        WHERE category = $1
        ORDER BY created_at DESC
        LIMIT 10
        """,
        category
    )


    text = (
        f"📂 <b>{category}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )


    for i, row in enumerate(rows, start=1):

        text += (
            f"{i}. 📌 <b>{row['title']}</b>\n"
            f"🔑 <code>{row['code']}</code>\n\n"
        )


    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📂 Kategori",
                    callback_data="store_category"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏪 Store",
                    callback_data="store"
                )
            ]
        ]
    )


    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )

    await call.answer()



# =========================
# SEARCH
# =========================

@router.callback_query(
    F.data == "store_search"
)
async def store_search(call: CallbackQuery):

    await call.message.answer(
        "🔎 Kirim nama code atau judul yang ingin dicari."
    )

    await call.answer()



@router.message(
    F.text
)
async def search_files(message: Message):

    keyword = message.text.strip()


    if len(keyword) < 3:
        return


    pool = await get_pool()


    rows = await pool.fetch(
        """
        SELECT
            code,
            title,
            price
        FROM files
        WHERE
            title ILIKE $1
            OR code ILIKE $1
        LIMIT 10
        """,
        f"%{keyword}%"
    )


    if not rows:
        return


    text = (
        "🔎 <b>HASIL PENCARIAN</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )


    for i, row in enumerate(rows, start=1):

        text += (
            f"{i}. 📌 <b>{row['title']}</b>\n"
            f"🔑 <code>{row['code']}</code>\n"
            f"💰 Rp{row['price']:,}\n\n"
        )


    await message.answer(
        text,
        parse_mode="HTML"
    )
