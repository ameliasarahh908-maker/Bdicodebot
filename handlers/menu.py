from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "🏪 Store")
async def store(message: Message):

    from handlers.store import store_command

    await store_command(message)



@router.message(F.text == "🏆 Top 10 Code")
async def top(message: Message):

    from handlers.top import top_command

    await top_command(message)
