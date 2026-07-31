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


def mask_code(code: str):
    if len(code) <= 8:
        return "*" * len(code)
    return code[:4] + "****" + code[-2:]


@router.callback_query(F.data.startswith("my_code"))
async def my_code(call: CallbackQuery):

    page = 1

    if ":" in call.data:
        try:
            page = int(call.data.split(":")[1])
        except:
            page = 1

    pool = await get_pool()

    total = await pool.fetchval(
        """
        SELECT COUNT(*)
        FROM files
        WHERE owner_id=$1
        """,
        call.from_user.id
    )

    if total == 0:

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Kembali",
                        callback_data="account"
                    )
                ]
            ]
        )

        return await call.message.edit_text(
            "📦 <b>MY CODE</b>\n\n"
            "❌ Kamu belum memiliki code.",
            parse_mode="HTML",
            reply_markup=kb
        )

    max_page = ceil(total / LIMIT)

    page = max(1, min(page, max_page))

    offset = (page - 1) * LIMIT

    rows = await pool.fetch(
        """
        SELECT
            code,
            price,
            sold_count,
            total_income
        FROM files
        WHERE owner_id=$1
        ORDER BY created_at DESC
        LIMIT $2 OFFSET $3
        """,
        call.from_user.id,
        LIMIT,
        offset
    )

    text = (
        "📦 <b>MY CODE</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"📄 Total Code : <b>{total}</b>\n"
        f"📑 Halaman : <b>{page}/{max_page}</b>\n\n"
    )

    for i, row in enumerate(rows, start=offset + 1):

        harga = (
            "Gratis"
            if row["price"] == 0
            else f"Rp {row['price']:,}".replace(",", ".")
        )

        text += (
            f"<b>{i}. <code>{mask_code(row['code'])}</code></b>\n"
            f"💰 Harga : {harga}\n"
            f"🛒 Terjual : {row['sold_count']}x\n"
            f"💵 Pendapatan : Rp {row['total_income']:,}\n\n"
            .replace(",", ".")
        )

    nav = []

    if page > 1:
        nav.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=f"my_code:{page-1}"
            )
        )

    nav.append(
        InlineKeyboardButton(
            text=f"{page}/{max_page}",
            callback_data="noop"
        )
    )

    if page < max_page:
        nav.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=f"my_code:{page+1}"
            )
        )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            nav,
            [
                InlineKeyboardButton(
                    text="⬅️ Kembali",
                    callback_data="account"
                )
            ]
        ]
    )

    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb
    )

    await call.answer()


@router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer()
