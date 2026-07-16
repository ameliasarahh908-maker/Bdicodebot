from aiogram import Router, types
from aiogram.filters import Command
import asyncio

from utils.user import set_vip, add_quota, get_quota

router = Router()


@router.message(Command("testvip"))
async def testvip(message: types.Message):

    user_id = message.from_user.id

    # ✅ SET VIP
    await set_vip(user_id, 1)

    # 🔥 anti race condition (WAJIB)
    await asyncio.sleep(0.2)

    # ✅ TAMBAH QUOTA
    await add_quota(user_id, 2)

    # 🔥 pastikan data sudah ke-save
    await asyncio.sleep(0.1)

    # ✅ AMBIL QUOTA
    quota = await get_quota(user_id)

    # ✅ RESPONSE
    await message.answer(
        f"✅ VIP aktif!\n"
        f"📦 Quota: {quota}"
    )
