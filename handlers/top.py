from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "🏆 Top Code")
async def top_code(message: Message):

    await message.answer(
        "<b><i>🏆 Top Code</i></b>\n\n"
        "<b><i>🚧 This feature is still under development.</i></b>",
        parse_mode="HTML"
    )
