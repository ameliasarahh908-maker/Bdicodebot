from aiogram import Router,F
from aiogram.types import Message

router=Router()

@router.message(F.text=="🏪 Store")
async def store(message:Message):
    await message.answer("Store sedang disiapkan.")

@router.message(F.text=="🏆 Top 10 Code")
async def top(message:Message):
    from handlers.top import top_command
    await top_command(message)

@router.message(F.text.in_(["👤 Akun","👤 Account"]))
async def account(message:Message):
    from handlers.account import account_menu
    await account_menu(message)

@router.message(F.text=="💎 Upgrade")
async def upgrade(message:Message):
    from handlers.vvip import vvip_menu
    await vvip_menu(message)
