from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from database import get_pool

router = Router()


# =========================
# MENU TOP FILE
# =========================
@router.callback_query(F.data == "top_file")
async def top_file(call: CallbackQuery):

    pool = await get_pool()

    rows = await pool.fetch(
        """
        SELECT
            code,
            title,
            buy_count,
            media_count,
            price
        FROM files
        WHERE is_paid = TRUE
        ORDER BY buy_count DESC
        LIMIT 10
        """
    )

    if not rows:
        await call.message.answer("❌ Belum ada data pembelian.")
        return await call.answer()

    text = (
        "🔥 <b>TOP 10 FILE PALING LARIS</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
    )

    for rank, row in enumerate(rows, start=1):

        text += (
            f"{rank}. 📌 <b>{row['title']}</b>\n"
            f"   🔑 <code>{row['code']}</code>\n"
            f"   💰 Harga : {row['price']}\n"
            f"   🛒 Dibeli : {row['buy_count']}x\n"
            f"   📦 Media : {row['media_count']} file\n\n"
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Kembali",
                    callback_data="home"
                )
            ]
        ]
    )

    await call.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )

    await call.answer()
