import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import TIMEZONE
from bot import bot, dp
from database import get_pool, close_db

# routers
from handlers.bayargg import router as bayargg_router
from handlers.start import router as start_router   # ⬅️ TAMBAH INI

# workers
from tasks.auto_delete import auto_delete_worker
from tasks.payment_worker import payment_worker
from tasks.vip_expired import vip_expired_worker


# =========================
# TIMEZONE
# =========================
os.environ["TZ"] = TIMEZONE
if hasattr(time, "tzset"):
    time.tzset()

# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

tasks = {}

# =========================
# TASK MANAGER
# =========================
def create_task(name, coro):
    if name in tasks and not tasks[name].done():
        logging.warning(f"{name} already running")
        return

    tasks[name] = asyncio.create_task(coro)
    logging.info(f"{name} started")


async def stop_task(name):
    task = tasks.get(name)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logging.info(f"{name} stopped")


# =========================
# START WORKERS
# =========================
async def start_workers():
    create_task("AUTO_DELETE", auto_delete_worker())
    create_task("PAYMENT", payment_worker())
    create_task("VIP_EXPIRED", vip_expired_worker())

    create_task(
        "POLLING",
        dp.start_polling(bot)
    )


# =========================
# FASTAPI LIFESPAN
# =========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("APP STARTING")

    await get_pool()
    await bot.delete_webhook(drop_pending_updates=True)

    me = await bot.get_me()
    logging.info(f"Bot: @{me.username}")

    # include routers
    dp.include_router(start_router)
    dp.include_router(bayargg_router)

    await start_workers()

    yield

    # shutdown
    logging.info("SHUTDOWN")

    for name in list(tasks.keys()):
        await stop_task(name)

    await close_db()
    await bot.session.close()

    logging.info("STOPPED")


# =========================
# APP
# =========================
app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok"}
