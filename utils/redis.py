import json
import asyncio
from typing import Any, Optional

import redis.asyncio as redis

# =========================
# CONFIG
# =========================
REDIS_URL = "redis://localhost:6379"

# Global instance
_redis: Optional[redis.Redis] = None


# =========================
# INIT
# =========================
async def init_redis():
    global _redis

    if _redis:
        return _redis

    _redis = redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        retry_on_timeout=True,
    )

    # test connection
    try:
        await _redis.ping()
        print("✅ Redis connected")
    except Exception as e:
        print("❌ Redis connection failed:", e)
        _redis = None

    return _redis


# =========================
# GET INSTANCE
# =========================
async def get_redis() -> Optional[redis.Redis]:
    global _redis

    if not _redis:
        await init_redis()

    return _redis


# =========================
# SAFE GET
# =========================
async def safe_get(key: str) -> Any:
    r = await get_redis()

    if not r:
        return None

    try:
        value = await r.get(key)

        if value is None:
            return None

        # coba parse JSON
        try:
            return json.loads(value)
        except:
            return value

    except Exception as e:
        print(f"Redis GET error: {e}")
        return None


# =========================
# SAFE SET
# =========================
async def safe_set(key: str, value: Any, ex: int = None):
    r = await get_redis()

    if not r:
        return

    try:
        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        await r.set(key, value, ex=ex)

    except Exception as e:
        print(f"Redis SET error: {e}")


# =========================
# DELETE
# =========================
async def safe_delete(key: str):
    r = await get_redis()

    if not r:
        return

    try:
        await r.delete(key)
    except Exception as e:
        print(f"Redis DELETE error: {e}")


# =========================
# EXISTS
# =========================
async def safe_exists(key: str) -> bool:
    r = await get_redis()

    if not r:
        return False

    try:
        return await r.exists(key) > 0
    except Exception as e:
        print(f"Redis EXISTS error: {e}")
        return False


# =========================
# INCR (counter)
# =========================
async def safe_incr(key: str, ex: int = None) -> int:
    r = await get_redis()

    if not r:
        return 0

    try:
        val = await r.incr(key)

        if ex:
            await r.expire(key, ex)

        return val

    except Exception as e:
        print(f"Redis INCR error: {e}")
        return 0
