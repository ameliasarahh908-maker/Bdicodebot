from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "🏪 Store")
async def store(message: Message):
    await message.answer("🏪 Store sedang disiapkan.")


@router.message(F.text == "🏆 Top 10 Code")
async def top(message: Message):
    from handlers.top import top_command
    await top_command(message)
