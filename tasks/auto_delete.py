import asyncio
import time

from utils.cache import NAV_CACHE


async def auto_delete_worker(bot):
    while True:
        now = time.time()

        to_delete = []

        for key, data in list(NAV_CACHE.items()):
            user_id, code = key
            msg_id, created_at, chat_id = data

            # hapus setelah 10 menit
            if now - created_at > 600:
                to_delete.append((key, msg_id, chat_id))

        for key, msg_id, chat_id in to_delete:
            try:
                await bot.delete_message(chat_id, msg_id)
            except:
                pass

            NAV_CACHE.pop(key, None)

        await asyncio.sleep(30)
