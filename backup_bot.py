import json
import logging
import asyncio

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties

from config import (
    BACKUP_BOT_TOKEN,
    STORAGE_CHANNEL_ID
)

from database import get_pool


# =========================
# LOG
# =========================
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


# =========================
# BOT INSTANCE
# =========================
backup_bot = Bot(
    token=BACKUP_BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode="HTML"
    )
)


backup_dp = Dispatcher()

router = Router()

backup_dp.include_router(router)



# =========================
# START LINK
# =========================
@router.message(CommandStart())
async def start_handler(message: Message):

    args = message.text.split()


    if len(args) < 2:

        return await message.answer(
            "🤖 Backup Bot Aktif\n\n"
            "Kirim kode file."
        )


    payload = args[1]


    if payload.startswith("getFile_"):

        code = payload.replace(
            "getFile_",
            ""
        )

        return await send_file(
            message,
            code
        )


    return await message.answer(
        "❌ Kode tidak valid."
    )



# =========================
# MANUAL CODE
# =========================
@router.message(F.text)
async def code_handler(message: Message):

    code = message.text.strip()


    if code.startswith("/"):

        return


    await send_file(
        message,
        code
    )



# =========================
# SEND FILE STORAGE
# =========================
async def send_file(
    message: Message,
    code: str
):

    pool = await get_pool()


    row = await pool.fetchrow(
        """
        SELECT
            title,
            media,
            is_paid,
            price
        FROM files
        WHERE code=$1
        """,
        code
    )


    if not row:

        return await message.answer(
            "❌ File tidak ditemukan."
        )


    if row["is_paid"]:

        return await message.answer(
            "🔒 File berbayar.\n"
            f"Harga: Rp {row['price']:,}".replace(",", ".")
        )



    # =========================
    # LOAD MEDIA
    # =========================
    try:

        media = json.loads(
            row["media"]
        )

    except Exception as e:

        logger.error(
            f"JSON ERROR: {e}"
        )

        return await message.answer(
            "❌ Data file rusak."
        )



    if not media:

        return await message.answer(
            "❌ File kosong."
        )



    await message.answer(
        f"📦 <b>{row['title']}</b>\n"
        f"📁 Total: {len(media)} file"
    )



    # =========================
    # COPY FROM STORAGE CHANNEL
    # =========================
    for item in media:

        try:

            storage_message_id = item.get(
                "message_id"
            )


            if not storage_message_id:

                continue



            await backup_bot.copy_message(
                chat_id=message.chat.id,

                from_chat_id=STORAGE_CHANNEL_ID,

                message_id=storage_message_id
            )


            # anti flood
            await asyncio.sleep(0.3)



        except Exception as e:

            logger.error(
                f"COPY STORAGE ERROR: {e}"
            )

            await message.answer(
                "❌ Gagal mengirim salah satu file."
            )
