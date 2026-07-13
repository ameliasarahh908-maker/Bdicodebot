from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from utils.redis_client import redis_client


# =========================
# BOT INIT
# =========================
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)


# =========================
# FSM STORAGE (REDIS / FALLBACK)
# =========================
if redis_client:
    storage = RedisStorage(redis_client)
else:
    storage = MemoryStorage()


dp = Dispatcher(storage=storage)


# =========================
# ROUTERS IMPORT
# =========================
from handlers.start import router as start_router
from handlers.check_sub import router as check_sub_router
from handlers.vip import router as vip_router
from handlers.search import router as search_router
from handlers.top import router as top_router

# =========================
# REGISTER ROUTERS
# =========================
dp.include_router(start_router)
dp.include_router(check_sub_router)
dp.include_router(vip_router)
dp.include_router(search_router)
dp.include_router(top_router)
