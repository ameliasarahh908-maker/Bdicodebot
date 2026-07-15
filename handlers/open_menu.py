from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from handlers.page import send_page
from handlers.sendall import send_all


router = Router()


def open_keyboard(code):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📂 Open Page",
                    callback_data=f"openpage:{code}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📤 Open All",
                    callback_data=f"openall:{code}"
                )
            ]
        ]
    )


@router.callback_query(
    F.data.startswith("openpage:")
)
async def open_page(call: CallbackQuery):

    code = call.data.split(":")[1]

    await call.answer()

    await send_page(
        bot=call.bot,
        chat_id=call.message.chat.id,
        code=code,
        page=1
    )


@router.callback_query(
    F.data.startswith("openall:")
)
async def open_all(call: CallbackQuery):

    code = call.data.split(":")[1]

    await call.answer()

    await send_all(
        bot=call.bot,
        chat_id=call.message.chat.id,
        code=code
    )
