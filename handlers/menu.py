from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "🏆 Top Code")
async def top_code(message: Message):

    await message.answer(
        "<b><i>🏆 TOP CODE</i></b>\n\n"
        "⚙️ This feature is still under development.",
        parse_mode="HTML"
    )


@router.message(F.text == "💰 Search Harga")
async def search_harga(message: Message):

    await message.answer(
        "<b><i>💰 SEARCH HARGA</i></b>\n\n"
        "⚙️ This feature is still under development.",
        parse_mode="HTML"
    )


@router.message(F.text == "🔎 Search Code")
async def search_code(message: Message):

    await message.answer(
        "<b><i>🔎 SEARCH CODE</i></b>\n\n"
        "⚙️ This feature is still under development.",
        parse_mode="HTML"
    )


@router.message(F.text == "💎 VIP / VVIP")
async def vip_vvip(message: Message):

    await message.answer(
        "<b><i>💎 VIP / VVIP</i></b>\n\n"
        "⚙️ This feature is still under development.",
        parse_mode="HTML"
    )
