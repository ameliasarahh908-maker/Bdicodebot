@router.message(Command("testvip"))
async def testvip(message: types.Message):

    user_id = message.from_user.id

    await set_vip(user_id, 1)
    await add_quota(user_id, 2)

    quota = await get_quota(user_id)

    await message.answer(f"✅ VIP aktif!\n📦 Quota: {quota}")
