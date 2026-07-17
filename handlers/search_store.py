from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from database import get_pool


router = Router()


class SearchStore(StatesGroup):
    waiting_keyword = State()


# =========================
# OPEN SEARCH
# =========================

@router.callback_query(
    F.data == "store_search"
)
async def store_search(
    call: CallbackQuery,
    state: FSMContext
):

    await state.set_state(
        SearchStore.waiting_keyword
    )

    await call.message.answer(
        "🔎 Kirim nama atau kode yang ingin dicari."
    )

    await call.answer()


# =========================
# SEARCH RESULT
# =========================

@router.message(
    SearchStore.waiting_keyword
)
async def search_result(
    message: Message,
    state: FSMContext
):

    keyword = message.text.strip()

    pool = await get_pool()

    rows = await pool.fetch(
        """
        SELECT
            code,
            title,
            price,
            view_count
        FROM files
        WHERE
            title ILIKE $1
            OR code ILIKE $1
        ORDER BY
            view_count DESC,
            created_at DESC
        LIMIT 10
        """,
        f"%{keyword}%"
    )

    await state.clear()

    if not rows:

        return await message.answer(
            "❌ Code tidak ditemukan."
        )

    text = (
        "🔎 <b>HASIL PENCARIAN</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )

    for i, row in enumerate(
        rows,
        start=1
    ):

        price = (
            "Gratis"
            if row["price"] == 0
            else f"Rp{row['price']:,}"
        )

        text += (
            f"{i}. 📌 <b>{row['title']}</b>\n"
            f"🔑 <code>{row['code']}</code>\n"
            f"💰 {price}\n"
            f"👁 {row['view_count']}x\n\n"
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

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )
