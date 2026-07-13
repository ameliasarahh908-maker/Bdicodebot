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

# workers
from tasks.auto_delete import auto_delete_worker
from tasks.payment_worker import payment_worker


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


# =========================
# GLOBAL TASKS
# =========================
tasks = {}


# =========================
# TASK WRAPPER (ANTI CRASH)
# =========================
async def task_wrapper(name, coro):
    try:
        logging.info(f"▶️ {name} started")
        await coro
    except asyncio.CancelledError:
        logging.info(f"⛔ {name} cancelled")
    except Exception:
        logging.exception(f"💥 {name} crashed")


# =========================
# SAFE CREATE TASK
# =========================
def create_task(name, coro):
    if name in tasks and not tasks[name].done():
        logging.warning(f"⚠️ {name} already running")
        return

    task = asyncio.create_task(task_wrapper(name, coro))
    tasks[name] = task


# =========================
# SAFE STOP TASK
# =========================
async def stop_task(name):
    task = tasks.get(name)

    if not task:
        return

    task.cancel()

    try:
        await asyncio.wait_for(task, timeout=5)
    except asyncio.TimeoutError:
        logging.warning(f"⚠️ {name} force killed")
    except asyncio.CancelledError:
        pass

    logging.info(f"❌ {name} stopped")


# =========================
# START WORKERS
# =========================
async def start_workers():

    create_task(
        "AUTO_DELETE",
        auto_delete_worker(bot)
    )

    create_task(
        "PAYMENT",
        payment_worker()
    )

    # ✅ polling bot (WAJIB cuma 1)
    create_task(
        "POLLING",
        dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    )
# =========================
# FASTAPI LIFESPAN
# =========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("🚀 APP STARTING...")

    # =========================
    # INIT DB
    # =========================
    await get_pool()

    # =========================
    # RESET TELEGRAM
    # =========================
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        logging.warning("⚠️ Failed delete webhook")

    me = await bot.get_me()
    logging.info(f"🤖 Logged in as @{me.username}")

    # =========================
    # START WORKERS
    # =========================
    await start_workers()

    yield

    # =========================
    # SHUTDOWN
    # =========================
    logging.info("🛑 SHUTDOWN...")

    # stop all tasks
    for name in list(tasks.keys()):
        await stop_task(name)

    # close DB
    await close_db()

    # close bot session
    await bot.session.close()

    logging.info("✅ APP STOPPED")


# =========================
# APP INIT
# =========================
app = FastAPI(lifespan=lifespan)

app.include_router(bayargg_router)


# =========================
# ROUTES
# =========================
@app.get("/")
async def root():
    return {"status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok"}
