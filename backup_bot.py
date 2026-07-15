import json
import logging
import asyncio
import re

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties

from config import (
    BACKUP_BOT_TOKEN,
    STORAGE_CHANNEL_ID,
    BOT_URL
)

from database import get_pool


# =========================
# LOG
# =========================
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


# =========================
# BOT
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
# NORMALIZE CODE
# =========================
def clean_code(text: str):

    text = text.strip()

    # buang link kalau user paste full link
    if "getFile_" in text:
        text = text.split("getFile_")[-1]

    # hapus karakter aneh
    text = re.sub(
        r"[^a-zA-Z0-9]",
        "",
        text
    )

    return text



# =========================
# START LINK
# =========================
@router.message(CommandStart())
async def start_handler(message: Message):

    args = message.text.split()


    if len(args) < 2:

        return await message.answer(
            "🤖 Backup Bot Aktif\n\n"
            "Tempel kode file."
        )


    payload = args[1]


    if "getFile_" in payload:

        code = payload.split(
            "getFile_"
        )[-1]

        return await send_file(
            message,
            code
        )


    return await message.answer(
        "❌ Link tidak valid."
    )



# =========================
# CODE HANDLER
# =========================
@router.message(F.text)
async def code_handler(message: Message):

    text = clean_code(
        message.text
    )


    if not text:
        return


    pool = await get_pool()


    # =========================
    # CARI CODE FLEXIBLE
    # =========================
    row = await pool.fetchrow(
        """
        SELECT code
        FROM files
        WHERE
            LOWER(code)=LOWER($1)
            OR LOWER(code) LIKE '%' || LOWER($1)
            OR LOWER($1) LIKE '%' || LOWER(code)
        LIMIT 1
        """,
        text
    )


    if row:

        return await send_file(
            message,
            row["code"]
        )


    # =========================
    # BUKAN CODE
    # =========================
    await message.answer(
        "🤖 Gunakan Bot Utama untuk upload, akun, dan fitur lainnya.\n\n"
        f"➡️ {BOT_URL}"
    )



# =========================
# SEND FILE
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
        WHERE LOWER(code)=LOWER($1)
        LIMIT 1
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
    # SEND MEDIA BY FILE_ID
    # =========================

    for item in media:

        try:

            file_id = item.get("file_id")
            file_type = item.get("type")


            if not file_id:
                continue


            if file_type == "video":

                await backup_bot.send_video(
                    chat_id=message.chat.id,
                    video=file_id
                )


            elif file_type == "photo":

                await backup_bot.send_photo(
                    chat_id=message.chat.id,
                    photo=file_id
                )


            elif file_type == "document":

                await backup_bot.send_document(
                    chat_id=message.chat.id,
                    document=file_id
                )


            elif file_type == "audio":

                await backup_bot.send_audio(
                    chat_id=message.chat.id,
                    audio=file_id
                )


            await asyncio.sleep(0.3)


        except Exception as e:

            logger.exception(
                f"SEND MEDIA ERROR: {e}"
            )
