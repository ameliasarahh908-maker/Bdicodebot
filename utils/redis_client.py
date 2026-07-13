import os
from redis.asyncio import Redis

REDIS_URL = os.getenv("REDIS_URL")

redis_client = None

if REDIS_URL:
    redis_client = Redis.from_url(
        REDIS_URL,
        decode_responses=True
    )
else:
    print("⚠️ REDIS_URL not set, Redis disabled")
