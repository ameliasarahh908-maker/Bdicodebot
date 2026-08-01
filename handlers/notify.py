import re

from aiogram import Router, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from database import get_pool

router = Router()


# =====================================
# REGEX CODE
# =====================================

CODE_REGEX = re.compile(
    r"[a-z0-9]{30,60}",
    re.IGNORECASE
)


def normalize_code(code: str):
    return (
        code
        .strip()
        .replace(" ", "")
        .replace("\n", "")
        .lower()
    )


# =====================================
# KEYBOARD
# =====================================

def kb_open():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📥 Buka File",
                    callback_data="getfile"
                )
            ]
        ]
    )


def kb_upload():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 Upload File",
                    callback_data="upfile"
                )
            ]
        ]
    )


def kb_home():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏠 Menu Utama",
                    callback_data="home"
                )
            ]
        ]
    )


# =====================================
# NOTIFY
# =====================================

@router.message(F.text)
async def notify_text(message: Message):

    text = (message.text or "").strip()

    # =====================================
    # MENU CHANNEL
    # =====================================

    keywords = {
        "group",
        "grup",
        "channel",
        "ch",
        "info"
    }

    if text.lower() in keywords:

        return await message.answer(
            (
                "📢 <b>MENU CHANNEL</b>\n\n"
                "Silakan tekan tombol di bawah untuk membuka menu Channel."
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📢 Channel",
                            callback_data="channel"
                        )
                    ]
                ]
            )
        )

    # =====================================
    # DETECT CODE
    # =====================================

    match = CODE_REGEX.search(text)

    if match:

        code = normalize_code(match.group(0))

        pool = await get_pool()

        exists = await pool.fetchval(
            """
            SELECT EXISTS(
                SELECT 1
                FROM files
                WHERE LOWER(TRIM(code))=$1
            )
            """,
            code
        )

        if exists:

            return await message.answer(
                (
                    "🔑 <b>CODE TERDETEKSI</b>\n\n"
                    "Saya menemukan kode file yang valid.\n\n"
                    "Tekan tombol di bawah untuk membuka file tersebut."
                ),
                parse_mode="HTML",
                reply_markup=kb_open()
            )

        return await message.answer(
            (
                "❌ <b>CODE TIDAK VALID</b>\n\n"
                "Kode yang Anda kirim tidak ditemukan atau bukan berasal dari bot ini."
            ),
            parse_mode="HTML",
            reply_markup=kb_home()
        )

    # =====================================
    # BUKAN CODE
    # =====================================

    return await message.answer(
        (
            "👋 <b>Halo!</b>\n\n"
            "Saya tidak menemukan kode file pada pesan Anda.\n\n"
            "• Jika ingin mengirim file, tekan <b>Upload File</b>.\n"
            "• Jika sudah memiliki CODE, kirim CODE tersebut ke chat ini."
        ),
        parse_mode="HTML",
        reply_markup=kb_upload()
    )


# =====================================
# DETECT MEDIA
# =====================================

@router.message(
    F.photo
    | F.video
    | F.document
    | F.audio
    | F.voice
    | F.animation
    | F.sticker
)
async def notify_media(message: Message):

    return await message.answer(
        (
            "📤 <b>MEDIA TERDETEKSI</b>\n\n"
            "Saya mendeteksi Anda mengirim media.\n\n"
            "Jika ingin menyimpan media ke bot, tekan tombol Upload File."
        ),
        parse_mode="HTML",
        reply_markup=kb_upload()
    )

# =====================================
# TEXT / COMMAND LAIN
# =====================================

@router.message(F.text.startswith("/"))
async def ignore_command(message: Message):
    return


@router.message()
async def notify_other(message: Message):

    return await message.answer(
        (
            "🤔 <b>Saya tidak memahami pesan tersebut.</b>\n\n"
            "📤 Kirim media untuk di-upload.\n"
            "🔑 Kirim CODE untuk membuka file.\n\n"
            "Atau tekan tombol di bawah untuk membuka menu utama."
        ),
        parse_mode="HTML",
        reply_markup=kb_home()
    )

