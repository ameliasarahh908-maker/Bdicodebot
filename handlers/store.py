from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database import get_pool
from keyboards.store import store_keyboard


router = Router()


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
        "📦 Total Code : "
        f"<b>{total_code:,}</b>\n"
        "👁 Total Dibuka : "
        f"<b>{total_view:,}</b>\n"
        "🛒 Total Pembelian : "
        f"<b>{total_buy:,}</b>\n\n"
        "Silakan pilih menu di bawah."
    )


    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=store_keyboard()
    )



# =========================
# REPLY BUTTON STORE
# =========================

@router.message(
    F.text == "🏪 Store"
)
async def store_menu(message: Message):

    await store_command(
        message
    )



# =========================
# INLINE BACK TO STORE
# =========================

@router.callback_query(
    F.data == "store"
)
async def store_callback(
    call: CallbackQuery
):

    try:
        await call.message.delete()
    except:
        pass


    await store_command(
        call.message
    )


    await call.answer()
