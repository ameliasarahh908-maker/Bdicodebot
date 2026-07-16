import json
import time
from datetime import datetime, timezone, timedelta

from utils.redis_client import safe_get, safe_set
from database import get_pool


def default_user():
    return {
        "level":"free",
        "expired_at":0,
        "paid_quota":0
    }


async def get_user_data(user_id:int):
    data = await safe_get(f"user:{user_id}")

    if not data:
        return default_user()

    if isinstance(data,bytes):
        data=data.decode()

    try:
        return json.loads(data)
    except:
        return default_user()


async def save_user_data(user_id:int,data:dict):
    await safe_set(
        f"user:{user_id}",
        json.dumps(data)
    )


# =========================
# USER STATUS DATABASE
# =========================
async def get_user_status(pool,user_id:int):

    user = await pool.fetchrow(
        """
        SELECT
            vip,
            vip_until,
            vvip,
            vvip_until,
            is_vip,
            vip_expired,
            is_vvip,
            vvip_expired
        FROM users
        WHERE telegram_id=$1
        """,
        user_id
    )

    if not user:
        return "free"


    now=datetime.now(timezone.utc)


    if (
        user["is_vvip"]
        and user["vvip_expired"]
        and user["vvvip_expired"] > now
    ):
        return "vvip"


    if (
        user["vvip"]
        and user["vvip_until"]
        and user["vvip_until"] > now
    ):
        return "vvip"


    if (
        user["is_vip"]
        and user["vip_expired"]
        and user["vip_expired"] > now
    ):
        return "vip"


    if (
        user["vip"]
        and user["vip_until"]
        and user["vip_until"] > now
    ):
        return "vip"


    await pool.execute(
        """
        UPDATE users
        SET
            vip=false,
            vvip=false,
            is_vip=false,
            is_vvip=false
        WHERE telegram_id=$1
        """,
        user_id
    )

    return "free"



# =========================
# SET VIP
# =========================
async def set_vip(user_id:int,days:int=30):

    pool=await get_pool()

    now=datetime.now(timezone.utc)

    user=await pool.fetchrow(
        """
        SELECT vip_until
        FROM users
        WHERE telegram_id=$1
        """,
        user_id
    )


    if user and user["vip_until"] and user["vip_until"]>now:
        expired=user["vip_until"]+timedelta(days=days)
    else:
        expired=now+timedelta(days=days)


    await pool.execute(
        """
        UPDATE users
        SET
            vip=true,
            is_vip=true,
            vip_until=$1,
            vip_expired=$1,
            plan='vip',
            expired_at=$1
        WHERE telegram_id=$2
        """,
        expired,
        user_id
    )

    return expired



# =========================
# SET VVIP
# =========================
async def set_vvip(user_id:int,days:int=7):

    pool=await get_pool()

    now=datetime.now(timezone.utc)


    user=await pool.fetchrow(
        """
        SELECT vvip_expired
        FROM users
        WHERE telegram_id=$1
        """,
        user_id
    )


    if user and user["vvvip_expired"] and user["vvip_expired"]>now:
        expired=user["vvip_expired"]+timedelta(days=days)
    else:
        expired=now+timedelta(days=days)


    await pool.execute(
        """
        UPDATE users
        SET
            vvip=true,
            is_vvip=true,
            vvip_until=$1,
            vvip_expired=$1,

            vip=true,
            is_vip=true,
            vip_until=$1,
            vip_expired=$1,

            plan='vvip',
            expired_at=$1

        WHERE telegram_id=$2
        """,
        expired,
        user_id
    )


    return expired



# =========================
# FREE
# =========================
async def set_free(user_id:int):

    pool=await get_pool()

    await pool.execute(
        """
        UPDATE users
        SET
            vip=false,
            vvip=false,
            is_vip=false,
            is_vvip=false,
            vip_until=NULL,
            vvip_until=NULL,
            vip_expired=NULL,
            vvip_expired=NULL,
            plan='free',
            expired_at=NULL
        WHERE telegram_id=$1
        """,
        user_id
    )


# =========================
# CHECK
# =========================
async def is_vip(user_id:int):

    pool=await get_pool()

    status=await get_user_status(
        pool,
        user_id
    )

    return status in ["vip","vvip"]


async def is_vvip(user_id:int):

    pool=await get_pool()

    status=await get_user_status(
        pool,
        user_id
    )

    return status=="vvip"



# =========================
# QUOTA REDIS
# =========================
async def add_quota(user_id:int,amount:int):

    data=await get_user_data(user_id)

    data["paid_quota"]=data.get(
        "paid_quota",0
    )+amount

    await save_user_data(
        user_id,
        data
    )


async def get_quota(user_id:int):

    data=await get_user_data(user_id)

    return data.get(
        "paid_quota",
        0
    )


async def use_quota(user_id:int):

    data=await get_user_data(user_id)

    quota=data.get(
        "paid_quota",
        0
    )

    if quota>0:

        data["paid_quota"]=quota-1

        await save_user_data(
            user_id,
            data
        )

        return True

    return False
