import asyncio
import time
from collections import defaultdict

# =========================
# CACHE STORAGE
# =========================

# (user_id, code) -> (page, timestamp)
PAGE_CACHE = {}

# (user_id, code) -> (last_page, timestamp)
PAGE_CHANGE = {}

# (user_id, code) -> message_id
NAV_CACHE = {}

# Lock per user biar gak spam klik
USER_LOCK = defaultdict(lambda: asyncio.Lock())


# =========================
# CACHE CLEANER LOOP
# =========================
async def clear_cache_loop():
    """
    Bersihin cache lama tiap 1 jam
    """
    while True:
        await asyncio.sleep(3600)

        now = time.time()

        for cache in [PAGE_CACHE, PAGE_CHANGE, NAV_CACHE]:

            to_delete = []

            for key, value in list(cache.items()):
                try:
                    # NAV_CACHE beda format (cuma message_id)
                    if isinstance(value, tuple):
                        ts = value[1]
                    else:
                        continue

                    if now - ts > 7200:  # expire 2 jam
                        to_delete.append(key)

                except:
                    continue

            for key in to_delete:
                cache.pop(key, None)

        print("🧹 Cache cleaned")
