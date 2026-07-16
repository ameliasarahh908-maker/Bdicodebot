import time
import json
from utils.redis import safe_get, safe_set


# 🔍 Ambil status user + auto handle expired
async def get_user_status(user_id: int) -> str:
    data = await safe_get(f"user:{user_id}")

    if not data:
        return "free"

    data = json.loads(data)

    level = data.get("level", "free")
    expired = data.get("expired_at", 0)

    # 👇 kalau VIP dan expired → jadi FREE
    if level == "vip" and expired < time.time():
        await safe_set(f"user:{user_id}", json.dumps({
            "level": "free",
            "expired_at": 0
        }))
        return "free"

    return level


# 💎 Set VIP (pakai durasi hari)
async def set_vip(user_id: int, days: int = 30):
    expired = int(time.time()) + (days * 86400)

    data = {
        "level": "vip",
        "expired_at": expired
    }

    await safe_set(f"user:{user_id}", json.dumps(data))


# 👑 Set VVIP (permanen)
async def set_vvip(user_id: int):
    data = {
        "level": "vvip",
        "expired_at": 9999999999
    }

    await safe_set(f"user:{user_id}", json.dumps(data))
