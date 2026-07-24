import re

from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

router = Router()

@router.message()
async def notify_user(message: Message, state: FSMContext):

    # Jangan ganggu jika sedang memakai FSM
    if await state.get_state():
        return

    # =========================
    # BIARKAN MEDIA DIPROSES HANDLER LAIN
    # =========================
    if (
        message.photo
        or message.video
        or message.document
        or message.audio
        or message.animation
        or message.voice
    ):
        return

    if not message.text:
        return

    text = message.text.strip()

    # =========================
    # ABAIKAN REPLY KEYBOARD
    # =========================
    if text in {
        "🏪 Store",
        "🏆 Top 10 Code",
        "👤 Akun",
        "👤 Account",
        "💎 Upgrade",
        "🎁 Reward"
    }:
        return

    # =========================
    # FORMAT KODE DIDUKUNG
    # =========================
    if re.search(
        r"Zyx\d{8}File\d{8}",
        text,
        re.IGNORECASE
    ):
        # biarkan handler getfile.py memproses
        return

    # =========================
    # FORMAT MIRIP TAPI SALAH
    # =========================
    if re.search(r"zyx|file", text, re.IGNORECASE):
        return await message.reply(
            "❌ Kode file tidak didukung atau formatnya salah."
        )

    # =========================
    # CHAT BIASA
    # =========================
    await message.reply(
        "👋 Silakan gunakan tombol menu di bawah untuk cari code."
    )
