from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from aiogram.fsm.storage.redis import RedisStorage

from config import BOT_TOKEN
from redis import redis


# =========================
# BOT INIT
# =========================
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)


# =========================
# FSM STORAGE REDIS
# =========================
storage = RedisStorage(redis)

dp = Dispatcher(
    storage=storage
)


# =========================
# ROUTERS IMPORT
# =========================
from handlers.start import router as start_router
from handlers.check_sub import router as check_sub_router


# =========================
# REGISTER ROUTERS
# =========================
dp.include_router(start_router)
dp.include_router(check_sub_router)
