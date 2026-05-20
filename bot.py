from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import asyncio

import os

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("✅ Bot aktif")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
