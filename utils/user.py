from datetime import datetime, timezone, timedelta
from database import get_pool


async def get_user_status(pool, user_id: int) -> str:
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

    now = datetime.now(timezone.utc)

    if (
        user["is_vvip"]
        and user["vvip_expired"]
        and user["vvip_expired"] > now
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
            is_vvip=false,
            plan='free'
        WHERE telegram_id=$1
        """,
        user_id
    )

    return "free"


async def set_vip(user_id: int, days: int = 30):
    pool = await get_pool()
    now = datetime.now(timezone.utc)

    user = await pool.fetchrow(
        """
        SELECT vip_until
        FROM users
        WHERE telegram_id=$1
        """,
        user_id
    )

    if user and user["vip_until"] and user["vip_until"] > now:
        expired = user["vip_until"] + timedelta(days=days)
    else:
        expired = now + timedelta(days=days)

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


async def set_vvip(user_id: int, days: int = 7):
    pool = await get_pool()
    now = datetime.now(timezone.utc)

    user = await pool.fetchrow(
        """
        SELECT vvip_expired
        FROM users
        WHERE telegram_id=$1
        """,
        user_id
    )

    if user and user["vvvip_expired"] and user["vvip_expired"] > now:
        expired = user["vvip_expired"] + timedelta(days=days)
    else:
        expired = now + timedelta(days=days)

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


async def set_free(user_id: int):
    pool = await get_pool()

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


async def is_vip(user_id: int):
    pool = await get_pool()

    status = await get_user_status(
        pool,
        user_id
    )

    return status in ["vip","vvip"]


async def is_vvip(user_id: int):
    pool = await get_pool()

    status = await get_user_status(
        pool,
        user_id
    )

    return status == "vvip"
