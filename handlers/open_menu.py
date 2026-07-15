from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from database import get_pool
from handlers.sendall import send_all
from handlers.page import send_page

router = Router()


def open_keyboard(code):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📂 Open Page",
                    callback_data=f"page:{code}:1"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📤 Open All",
                    callback_data=f"all:{code}"
                )
            ]
        ]
    )


@router.callback_query(F.data.startswith("page:"))
async def open_page(call: CallbackQuery):
    try:
        _, code, page = call.data.split(":")
        page = int(page)
    except:
        return await call.answer(
            "❌ Data salah",
            show_alert=True
        )

    await call.answer()

    await send_page(
        bot=call.bot,
        chat_id=call.message.chat.id,
        user_id=call.from_user.id,
        code=code,
        page=page
    )


@router.callback_query(F.data.startswith("all:"))
async def open_all(call: CallbackQuery):
    code = call.data.split(":")[1]

    pool = await get_pool()

    file = await pool.fetchrow(
        """
        SELECT *
        FROM files
        WHERE LOWER(code)=LOWER($1)
        LIMIT 1
        """,
        code
    )

    if not file:
        return await call.answer(
            "❌ File tidak ditemukan",
            show_alert=True
        )

    await call.answer()

    await send_all(
        bot=call.bot,
        chat_id=call.message.chat.id,
        code=code,
        file=file
    )
