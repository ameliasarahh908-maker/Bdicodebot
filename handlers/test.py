from aiogram import Router, types
from aiogram.filters import Command

from utils.user import set_vip, add_quota, get_quota

router = Router()


@router.message(Command("testvip"))
async def testvip(message: types.Message):

    user_id = message.from_user.id

    await set_vip(user_id, 1)
    await add_quota(user_id, 2)

    quota = await get_quota(user_id)

    await message.answer(f"VIP aktif!\nQuota: {quota}")
