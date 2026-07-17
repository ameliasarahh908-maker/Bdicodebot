from math import ceil

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from database import get_pool

router = Router()

LIMIT = 10


async def send_top(target, page: int = 1):

    pool = await get_pool()

    total = await pool.fetchval(
        "SELECT COUNT(*) FROM files"
    )

    if total == 0:
        text = "❌ Belum ada data."
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 Kembali",
                        callback_data="home"
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

    max_page = ceil(total / LIMIT)

    if page < 1:
        page = 1

    if page > max_page:
        page = max_page

    offset = (page - 1) * LIMIT

    rows = await pool.fetch(
        """
        SELECT
            code,
            title,
            view_count
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
        "🏆 <b>TOP 10 CODE TERPOPULER</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )

    start = offset + 1

    for i, row in enumerate(rows, start=start):

        if i == 1:
            rank = "🥇"
        elif i == 2:
            rank = "🥈"
        elif i == 3:
            rank = "🥉"
        else:
            rank = f"{i}."

        text += (
            f"{rank} <b>{row['title']}</b>\n"
            f"🔑 <code>{row['code']}</code>\n"
            f"👁 Dibuka : <b>{row['view_count']}</b>x\n\n"
        )

    nav = []

    if page > 1:
        nav.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=f"top:{page-1}"
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
                callback_data=f"top:{page+1}"
            )
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            nav,
            [
                InlineKeyboardButton(
                    text="🔙 Kembali",
                    callback_data="home"
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


async def top_command(message: Message):
    await send_top(message, 1)


@router.message(F.text == "🏆 Top 10 Code")
async def top_menu(message: Message):
    await send_top(message, 1)


@router.callback_query(F.data.startswith("top:"))
async def top_page(call: CallbackQuery):

    page = int(call.data.split(":")[1])

    await send_top(call, page)

    await call.answer()


@router.callback_query(F.data == "ignore")
async def ignore(call: CallbackQuery):
    await call.answer()
