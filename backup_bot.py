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
# BOT INSTANCE
# =========================
backup_bot = Bot(
    token=BACKUP_BOT_TOKEN
)

backup_dp = Dispatcher()

router = Router()

backup_dp.include_router(router)


# =========================
# START GET FILE
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
            f"Harga: Rp {row['price']:,}"
            .replace(",", ".")
        )


    media = json.loads(
        row["media"]
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
                f"SEND ERROR: {e}"
            )
