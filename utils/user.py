import time
import json
from utils.redis_client import safe_get, safe_set


# =========================
# GET USER STATUS
# =========================
async def get_user_status(user_id: int) -> str:

    data = await safe_get(
        f"user:{user_id}"
    )

    if not data:
        return "free"


    if isinstance(data, bytes):
        data = data.decode()


    data = json.loads(data)


    level = data.get(
        "level",
        "free"
    )

    expired_at = data.get(
        "expired_at",
        0
    )


    now = int(time.time())


    # =========================
    # VIP EXPIRED
    # =========================
    if level == "vip":

        if expired_at <= now:

            await safe_set(
                f"user:{user_id}",
                json.dumps({
                    "level": "free",
                    "expired_at": 0
                })
            )

            return "free"



    # =========================
    # VVIP PERMANEN
    # =========================
    if level == "vvip":
        return "vvip"


    return level



# =========================
# SET VIP
# =========================
async def set_vip(
    user_id: int,
    days: int = 30
):

    expired = int(time.time()) + (
        days * 86400
    )


    await safe_set(
        f"user:{user_id}",
        json.dumps({
            "level": "vip",
            "expired_at": expired
        })
    )



# =========================
# SET VVIP
# =========================
async def set_vvip(
    user_id: int
):

    await safe_set(
        f"user:{user_id}",
        json.dumps({
            "level": "vvip",
            "expired_at": 9999999999
        })
    )



# =========================
# SET FREE
# =========================
async def set_free(
    user_id:int
):

    await safe_set(
        f"user:{user_id}",
        json.dumps({
            "level":"free",
            "expired_at":0
        })
    )
