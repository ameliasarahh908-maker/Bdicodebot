import json
import logging
import asyncio

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties  # ✅ TAMBAHAN

from config import BACKUP_BOT_TOKEN
from database import get_pool


# =========================
# LOG
# =========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =========================
# BOT INSTANCE (FIX)
# =========================
backup_bot = Bot(
    token=BACKUP_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")  # ✅ FIX
)

backup_dp = Dispatcher()
router = Router()
backup_dp.include_router(router)


# =========================
# START (LINK HANDLER)
# =========================
@router.message(CommandStart())
async def start_handler(message: Message):

    print("TEXT MASUK:", message.text)  # 🔥 DEBUG

    args = message.text.split()

    # kalau cuma /start
    if len(args) < 2:
        return await message.answer(
            "🤖 Backup Bot Aktif\n\nKirim kode file."
        )

    payload = args[1]

    # validasi format link
    if payload.startswith("getFile_"):
        code = payload.replace("getFile_", "")
        return await send_file(message, code)

    return await message.answer("❌ Kode tidak valid.")


# =========================
# MANUAL CODE HANDLER
# =========================
@router.message(F.text)
async def code_handler(message: Message):

    code = message.text.strip()

    # biar gak bentrok sama /start
    if code.startswith("/"):
        return

    await send_file(message, code)


# =========================
# SEND FILE
# =========================
async def send_file(message: Message, code: str):

    pool = await get_pool()

    row = await pool.fetchrow(
        """
        SELECT title, media, is_paid, price
        FROM files
        WHERE code=$1
        """,
        code
    )

    if not row:
        return await message.answer("❌ File tidak ditemukan.")

    if row["is_paid"]:
        return await message.answer(
            "🔒 File berbayar.\n"
            f"Harga: Rp {row['price']:,}".replace(",", ".")
        )

    # =========================
    # LOAD MEDIA
    # =========================
    try:
        media = json.loads(row["media"])
    except Exception:
        return await message.answer("❌ Media rusak.")

    if not media:
        return await message.answer("❌ File kosong.")

    # =========================
    # INFO
    # =========================
    await message.answer(
        f"📦 <b>{row['title']}</b>\n"
        f"📁 Total: {len(media)} file"
    )

    # =========================
    # SEND FILE
    # =========================
    for item in media:

        try:
            file_id = item.get("file_id")
            file_type = item.get("type", "document")

            if not file_id:
                continue

            if file_type == "video":
                await message.answer_video(file_id)

            elif file_type == "photo":
                await message.answer_photo(file_id)

            else:
                await message.answer_document(file_id)

            # 🔥 anti flood
            await asyncio.sleep(0.2)

        except Exception as e:
            logger.error(f"SEND ERROR: {e}")
