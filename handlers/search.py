from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "🔎 Search Code")
async def search_code(message: Message):

    await message.answer(
        "<b><i>🔎 Search Code</i></b>\n\n"
        "<b><i>🚧 This feature is still under development.</i></b>",
        parse_mode="HTML"
    )


@router.message(F.text == "💰 Search Price")
async def search_price(message: Message):

    await message.answer(
        "<b><i>💰 Search Price</i></b>\n\n"
        "<b><i>🚧 This feature is still under development.</i></b>",
        parse_mode="HTML"
    )
