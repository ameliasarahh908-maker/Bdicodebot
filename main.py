import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import (
    TIMEZONE,
    BACKUP_BOT_TOKEN
)

from bot import bot, dp
from database import get_pool, close_db

# backup bot
if BACKUP_BOT_TOKEN:
    from backup_bot import backup_bot, backup_dp


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
        logging.warning(
            f"{name} already running"
        )
        return

    tasks[name] = asyncio.create_task(coro)

    logging.info(
        f"{name} started"
    )


async def stop_task(name):

    task = tasks.get(name)

    if task:

        task.cancel()

        try:
            await task

        except asyncio.CancelledError:
            logging.info(
                f"{name} stopped"
            )


# =========================
# START WORKERS
# =========================
async def start_workers():


    # SYSTEM WORKERS
    create_task(
        "AUTO_DELETE",
        auto_delete_worker()
    )

    create_task(
        "PAYMENT",
        payment_worker()
    )

    create_task(
        "VIP_EXPIRED",
        vip_expired_worker()
    )


    # =====================
    # MAIN BOT
    # =====================
    create_task(
        "MAIN_BOT",
        dp.start_polling(bot)
    )


    # =====================
    # BACKUP BOT
    # =====================
    if BACKUP_BOT_TOKEN:

        create_task(
            "BACKUP_BOT",
            backup_dp.start_polling(
                backup_bot
            )
        )

        logging.info(
            "Backup bot enabled"
        )

    else:

        logging.info(
            "Backup bot disabled"
        )



# =========================
# FASTAPI LIFESPAN
# =========================
@asynccontextmanager
async def lifespan(app: FastAPI):

    logging.info(
        "APP STARTING"
    )


    await get_pool()


    # MAIN BOT
    await bot.delete_webhook(
        drop_pending_updates=True
    )


    me = await bot.get_me()

    logging.info(
        f"Main Bot: @{me.username}"
    )


    # BACKUP BOT
    if BACKUP_BOT_TOKEN:

        await backup_bot.delete_webhook(
            drop_pending_updates=True
        )

        backup_me = await backup_bot.get_me()

        logging.info(
            f"Backup Bot: @{backup_me.username}"
        )


    await start_workers()


    yield



    # =====================
    # SHUTDOWN
    # =====================
    logging.info(
        "SHUTDOWN"
    )


    for name in list(tasks.keys()):
        await stop_task(name)


    await close_db()


    await bot.session.close()


    if BACKUP_BOT_TOKEN:
        await backup_bot.session.close()


    logging.info(
        "STOPPED"
    )



# =========================
# APP
# =========================
app = FastAPI(
    lifespan=lifespan
)


@app.get("/")
async def root():

    return {
        "status": "running"
    }


@app.get("/health")
async def health():

    return {
        "status": "ok"
    }
