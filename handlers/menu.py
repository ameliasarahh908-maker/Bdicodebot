from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "🏆 Top Code")
async def top_code(message: Message):

    await message.answer(
        "<b><i>🏆 TOP CODE</i></b>\n\n"
        "<i>🚧 This feature is still under development.</i>",
        parse_mode="HTML"
    )


@router.message(F.text == "💰 Search Price")
async def search_harga(message: Message):

    await message.answer(
        "<b><i>💰 SEARCH PRICE</i></b>\n\n"
        "<i>🚧 This feature is still under development.</i>",
        parse_mode="HTML"
    )


@router.message(F.text == "🔎 Search Code")
async def search_code(message: Message):

    await message.answer(
        "<b><i>🔎 SEARCH CODE</i></b>\n\n"
        "<i>🚧 This feature is still under development.</i>",
        parse_mode="HTML"
    )
