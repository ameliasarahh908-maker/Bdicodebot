import time
import json
from utils.redis_client import safe_get, safe_set

def default_user():
    return {"level": "free","expired_at": 0,"paid_quota": 0}

async def get_user_data(user_id: int):
    data = await safe_get(f"user:{user_id}")
    if not data:
        return default_user()
    if isinstance(data, bytes):
        data = data.decode()
    try:
        return json.loads(data)
    except:
        return default_user()

async def save_user_data(user_id: int, data: dict):
    await safe_set(f"user:{user_id}", json.dumps(data))

async def get_user_status(user_id: int) -> str:
    data = await get_user_data(user_id)
    level = data.get("level", "free")
    expired_at = data.get("expired_at", 0)
    now = int(time.time())

    # 🔥 FIX: handle VIP & VVIP expired
    if level in ["vip", "vvip"] and expired_at <= now:
        await save_user_data(user_id, default_user())
        return "free"

    return level

async def set_vip(user_id: int, days: int = 30):
    data = await get_user_data(user_id)
    expired = int(time.time()) + (days * 86400)
    new_data = {
        "level": "vip",
        "expired_at": expired,
        "paid_quota": data.get("paid_quota", 0)
    }
    await save_user_data(user_id, new_data)

async def set_vvip(user_id: int, days: int = 7):
    data = await get_user_data(user_id)
    expired = int(time.time()) + (days * 86400)
    data["level"] = "vvip"
    data["expired_at"] = expired
    data["paid_quota"] = 999999
    await save_user_data(user_id, data)

async def set_free(user_id: int):
    await save_user_data(user_id, default_user())

async def add_quota(user_id: int, amount: int):
    data = await get_user_data(user_id)
    data["paid_quota"] = data.get("paid_quota", 0) + amount
    await save_user_data(user_id, data)

async def add_referral(user_id: int):
    data = await get_user_data(user_id)
    data["referral_count"] = data.get("referral_count", 0) + 1
    await save_user_data(user_id, data)
    return data["referral_count"]

async def get_quota(user_id: int) -> int:
    data = await get_user_data(user_id)
    return data.get("paid_quota", 0)

async def use_quota(user_id: int) -> bool:
    data = await get_user_data(user_id)
    quota = data.get("paid_quota", 0)
    if quota > 0:
        data["paid_quota"] = quota - 1
        await save_user_data(user_id, data)
        return True
    return False
