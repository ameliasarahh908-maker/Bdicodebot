from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "💎 VIP / VVIP")
async def vip_vvip(message: Message):

    await message.answer(
        "<b><i>💎 VIP / VVIP</i></b>\n\n"
        "<b><i>🚧 This feature is still under development.</i></b>",
        parse_mode="HTML"
    )
