import time
import json
from utils.redis_client import safe_get, safe_set


# =========================
# HELPER
# =========================
def default_user():
    return {
        "level": "free",
        "expired_at": 0,
        "paid_quota": 0
    }


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
    await safe_set(
        f"user:{user_id}",
        json.dumps(data)
    )


# =========================
# GET USER STATUS
# =========================
async def get_user_status(user_id: int) -> str:

    data = await get_user_data(user_id)

    level = data.get("level", "free")
    expired_at = data.get("expired_at", 0)

    now = int(time.time())

    # =========================
    # VIP EXPIRED
    # =========================
    if level == "vip" and expired_at <= now:

        data = default_user()
        await save_user_data(user_id, data)

        return "free"

    return level


# =========================
# SET VIP
# =========================
async def set_vip(user_id: int, days: int = 30):

    data = await get_user_data(user_id)

    expired = int(time.time()) + (days * 86400)

    # 🔥 JANGAN HILANGKAN DATA LAMA
    data["level"] = "vip"
    data["expired_at"] = expired

    # 🔥 pastikan quota tetap ada
    data["paid_quota"] = data.get("paid_quota", 0)

    await save_user_data(user_id, data)


# =========================
# SET VVIP
# =========================
async def set_vvip(user_id: int, days: int = 7):

    data = await get_user_data(user_id)

    expired = int(time.time()) + (days * 86400)

    data["level"] = "vvip"
    data["expired_at"] = expired
    data["paid_quota"] = 999999  # unlimited

    await save_user_data(user_id, data)


# =========================
# SET FREE
# =========================
async def set_free(user_id: int):

    await save_user_data(user_id, default_user())


# =========================
# ADD QUOTA
# =========================
async def add_quota(user_id: int, amount: int):

    data = await get_user_data(user_id)

    data["paid_quota"] = data.get("paid_quota", 0) + amount

    await save_user_data(user_id, data)


# =========================
# GET QUOTA
# =========================
async def get_quota(user_id: int) -> int:

    data = await get_user_data(user_id)

    return data.get("paid_quota", 0)


# =========================
# USE QUOTA
# =========================
async def use_quota(user_id: int) -> bool:

    data = await get_user_data(user_id)

    quota = data.get("paid_quota", 0)

    if quota > 0:
        data["paid_quota"] = quota - 1
        await save_user_data(user_id, data)
        return True

    return False
