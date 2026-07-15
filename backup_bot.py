import asyncio
import json
import logging

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart

from config import BACKUP_BOT_TOKEN
from database import get_pool


# =========================
# LOG
# =========================
logging.basicConfig(
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# =========================
# BOT
# =========================
bot = Bot(
    token=BACKUP_BOT_TOKEN
)

dp = Dispatcher()

router = Router()

dp.include_router(router)


# =========================
# START GET FILE
# =========================
@router.message(CommandStart())
async def start_handler(message: Message):

    args = message.text.split()

    if len(args) < 2:
        return await message.answer(
            "🤖 Backup Bot Aktif\n\n"
            "Masukkan kode file."
        )


    payload = args[1]


    if not payload.startswith("getFile_"):
        return await message.answer(
            "❌ Kode tidak valid."
        )


    code = payload.replace(
        "getFile_",
        ""
    )


    await send_file(
        message,
        code
    )



# =========================
# CODE HANDLER
# =========================
@router.message(
    F.text.regexp(r"^zyxfidxbot")
)
async def code_handler(message: Message):

    code = message.text.strip()

    await send_file(
        message,
        code
    )



# =========================
# SEND MEDIA
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


    media = json.loads(
        row["media"]
    )


    if row["is_paid"]:

        return await message.answer(
            "🔒 File ini berbayar.\n"
            f"Harga: Rp {row['price']:,}"
            .replace(",", ".")
        )


    await message.answer(
        f"📦 <b>{row['title']}</b>\n"
        f"📁 Total: {len(media)} file",
        parse_mode="HTML"
    )


    for item in media:

        try:

            file_id = item["file_id"]
            file_type = item["type"]


            if file_type == "video":

                await message.answer_video(
                    file_id
                )


            elif file_type == "photo":

                await message.answer_photo(
                    file_id
                )


            else:

                await message.answer_document(
                    file_id
                )


        except Exception as e:

            logger.error(
                f"SEND ERROR {e}"
            )


# =========================
# MAIN
# =========================
async def main():

    logger.info(
        "BACKUP BOT STARTED"
    )


    await dp.start_polling(
        bot
    )


if __name__ == "__main__":

    asyncio.run(main())
