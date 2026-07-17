from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database import get_pool
from keyboards.store import store_keyboard


router = Router()


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
        "Temukan berbagai code "
        "premium maupun gratis.\n\n"
        f"📦 Total Code : <b>{total_code:,}</b>\n"
        f"👁 Total Dibuka : <b>{total_view:,}</b>\n"
        f"🛒 Total Pembelian : <b>{total_buy:,}</b>\n\n"
        "Silakan pilih menu."
    )


    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=store_keyboard()
    )



@router.message(
    F.text == "🏪 Store"
)
async def store_menu(message: Message):

    await store_command(
        message
    )



@router.callback_query(
    F.data == "store"
)
async def store_callback(call: CallbackQuery):

    try:
        await call.message.delete()
    except:
        pass


    await store_command(
        call.message
    )


    await call.answer()



@router.callback_query(
    F.data == "store_free"
)
async def store_free(
    call: CallbackQuery
):

    pool = await get_pool()

    rows = await pool.fetch(
        """
        SELECT
            code,
            title
        FROM files
        WHERE price = 0
        ORDER BY created_at DESC
        LIMIT 10
        """
    )


    if not rows:

        return await call.answer(
            "Belum ada code gratis.",
            show_alert=True
        )


    text = (
        "🆓 <b>CODE GRATIS</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )


    for i, row in enumerate(rows, 1):

        text += (
            f"{i}. 📌 <b>{row['title']}</b>\n"
            f"🔑 <code>{row['code']}</code>\n\n"
        )


    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏪 Kembali Store",
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

@router.callback_query(
    F.data == "store_random"
)
async def store_random(
    call: CallbackQuery
):

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


    for i, row in enumerate(rows, 1):

        text += (
            f"{i}. 📌 <b>{row['title']}</b>\n"
            f"🔑 <code>{row['code']}</code>\n"
            f"💰 Rp{row['price']:,}\n\n"
        )


    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🏪 Kembali Store",
                        callback_data="store"
                    )
                ]
            ]
        )
    )

    await call.answer()


