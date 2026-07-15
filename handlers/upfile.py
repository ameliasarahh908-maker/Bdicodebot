import asyncio
import json
import random
import string
import time
import logging
from typing import Dict

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import (
    CHANNEL_ID,
    STORAGE_CHANNEL_ID,
    BOT_URL,
    BOT_USERNAME,
    BACKUP_BOT_URL,
    BACKUP_BOT_USERNAME
)
from database import get_pool
from utils.force_sub import check_force_sub
from keyboards.join import join_kb

router = Router()

# =========================
# CONFIG
# =========================
MAX_MEDIA = 200
UPDATE_DELAY = 0.3

_last_update: Dict[int, float] = {}
_user_locks: Dict[int, asyncio.Lock] = {}

def get_lock(user_id: int):
    if user_id not in _user_locks:
        _user_locks[user_id] = asyncio.Lock()
    return _user_locks[user_id]


# ✅ TAMBAH DI SINI
from contextlib import asynccontextmanager

@asynccontextmanager
async def user_lock(user_id: int):
    lock = get_lock(user_id)
    async with lock:
        yield

# =========================
# SAFE EDIT
# =========================
async def safe_update(bot, chat_id, message_id, text, reply_markup=None):

    now = time.time()
    last = _last_update.get(chat_id, 0)

    if now - last < UPDATE_DELAY:
        return

    _last_update[chat_id] = now

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

    except TelegramBadRequest:
        pass

    except Exception as e:
        logging.error(f"SAFE UPDATE ERROR: {e}")


# =========================
# STATE
# =========================
class UploadState(StatesGroup):
    upload = State()
    wait_title = State()
    wait_price = State()

# =========================
# START UPLOAD
# =========================
@router.callback_query(F.data == "upfile")
async def start_upfile(call: CallbackQuery, state: FSMContext):

    await call.answer()

    async with user_lock(call.from_user.id):

        await state.clear()
        await state.set_state(UploadState.upload)

        # =========================
        # FORCE SUB
        # =========================
        if not await check_force_sub(
            call.bot,
            call.from_user.id
        ):
            return await call.message.answer(
                "❌ Join channel terlebih dahulu.",
                reply_markup=join_kb()
            )


        # =========================
        # DELETE OLD MENU
        # =========================
        try:
            await call.message.delete()
        except:
            pass


        # =========================
        # CREATE UPLOAD MESSAGE
        # =========================
        msg = await call.message.answer(
            "📦 <b>UPLOAD MODE ACTIVE</b>\n\n"
            "📤 Kirim foto, video atau dokumen.\n"
            "Maksimal <b>200 file</b>.\n\n"
            "Setelah selesai kirim file,\n"
            "tombol <b>STOP & SAVE</b> akan muncul.",
            parse_mode="HTML"
        )


        # =========================
        # SAVE SESSION
        # =========================
        await state.update_data(
            upload_mode=True,

            # media
            media=[],

            # info
            title=None,

            # share
            share_media=True,

            # payment
            is_paid=False,
            price=0,
            payment_provider=None,

            # counter
            view_count=0,
            download_count=0,
            favorite_count=0,

            # progress
            progress_msg_id=msg.message_id,

            # lock
            saving=False
        )


# =========================
# RECEIVE MEDIA (STORAGE CHANNEL FIX)
# =========================
@router.message(F.document | F.video | F.photo)
async def receive_media(message: Message, state: FSMContext):

    async with user_lock(message.from_user.id):

        data = await state.get_data()

        if not data.get("upload_mode"):
            return

        media = data.get("media", [])

        if len(media) >= MAX_MEDIA:
            return await message.answer(
                f"❌ Maksimal {MAX_MEDIA} file."
            )


        # =========================
        # COPY KE STORAGE CHANNEL
        # =========================
        try:

            copy = await message.bot.copy_message(
                chat_id=STORAGE_CHANNEL_ID,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )

            storage_message_id = copy.message_id

        except Exception as e:

            logging.error(
                f"STORAGE COPY ERROR: {e}"
            )

            return await message.answer(
                "❌ Gagal menyimpan file."
            )


        # =========================
        # TYPE INFO
        # =========================
        if message.document:

            media_type = "document"
            file_name = message.document.file_name
            file_size = message.document.file_size


        elif message.video:

            media_type = "video"
            file_name = getattr(
                message.video,
                "file_name",
                None
            )
            file_size = message.video.file_size


        else:

            media_type = "photo"
            file_name = None
            file_size = message.photo[-1].file_size



        # =========================
        # DUPLICATE CHECK
        # =========================
        if any(
            x["message_id"] == storage_message_id
            for x in media
        ):
            return



        # =========================
        # SAVE SESSION
        # =========================
        media.append({

            "message_id": storage_message_id,

            "type": media_type,

            "file_name": file_name,

            "file_size": file_size

        })


        await state.update_data(
            media=media
        )


        # =========================
        # DELETE ORIGINAL
        # =========================
        try:
            await message.delete()
        except:
            pass



        # =========================
        # NOTIF
        # =========================
        notif = await message.answer(
            f"✅ File diterima ({len(media)}/{MAX_MEDIA})"
        )


        await asyncio.sleep(1.5)


        try:
            await notif.delete()
        except:
            pass



        # =========================
        # UPDATE PROGRESS
        # =========================
        text = (
            "📦 <b>UPLOAD MODE</b>\n\n"
            f"📁 Total File: <b>{len(media)}</b>\n\n"
            "Jika sudah selesai tekan tombol di bawah."
        )


        kb = InlineKeyboardBuilder()

        kb.button(
            text="⏹ STOP & SAVE",
            callback_data="save_upfile"
        )

        kb.button(
            text="❌ BATAL",
            callback_data="cancel_upfile"
        )

        kb.adjust(1)



        old_id = data.get(
            "progress_msg_id"
        )


        if old_id:

            await safe_update(
                message.bot,
                message.chat.id,
                old_id,
                text,
                kb.as_markup()
            )


        else:

            sent = await message.answer(
                text,
                reply_markup=kb.as_markup(),
                parse_mode="HTML"
            )

            await state.update_data(
                progress_msg_id=sent.message_id
            )


# =========================
# CANCEL
# =========================
@router.callback_query(F.data == "cancel_upfile")
async def cancel(call: CallbackQuery, state: FSMContext):

    await call.answer()

    async with user_lock(call.from_user.id):

        data = await state.get_data()
        msg_id = data.get("progress_msg_id")

        try:
            if msg_id:
                await call.bot.delete_message(
                    call.message.chat.id,
                    msg_id
                )
        except:
            pass

        try:
            await call.message.edit_text(
                "❌ <b>UPLOAD DIBATALKAN</b>",
                parse_mode="HTML"
            )
        except:
            pass

        await state.clear()

# =========================
# SAVE → SHARE MODE
# =========================
@router.callback_query(F.data == "save_upfile")
async def choose_share(call: CallbackQuery, state: FSMContext):

    await call.answer()

    async with user_lock(call.from_user.id):

        data = await state.get_data()

        # =========================
        # 🔥 ANTI DOUBLE CLICK
        # =========================
        if data.get("saving"):
            return await call.answer(
                "Sedang diproses...",
                show_alert=True
            )

        # aktifkan lock
        await state.update_data(saving=True)

        # =========================
        # VALIDASI MEDIA
        # =========================
        if not data.get("media"):
            await state.update_data(saving=False)
            return await call.answer(
                "Belum ada file.",
                show_alert=True
            )

        # =========================
        # UI PILIH MODE
        # =========================
        kb = InlineKeyboardBuilder()

        kb.button(
            text="🔗 SHARE MEDIA",
            callback_data="share_yes"
        )

        kb.button(
            text="🔒 PRIVATE",
            callback_data="share_no"
        )

        kb.adjust(2)

        await call.message.edit_text(
            "📦 <b>PILIH MODE FILE</b>\n\n"
            "🔗 Share Media = File dapat dibagikan.\n"
            "🔒 Private = Hanya melalui kode.",
            parse_mode="HTML",
            reply_markup=kb.as_markup()
        )

        # =========================
        # ❗ BUKA LOCK LAGI
        # =========================
        await state.update_data(saving=False)

# =========================
# INPUT TITLE
# =========================
import re

BAD_WORDS = ["bocil", "child", "underage"]

# =========================
# NORMALIZE (ANTI AKALIN)
# =========================
def normalize(text: str) -> str:
    return re.sub(r'[^a-z0-9]', '', text.lower())

# =========================
# CHECK BAD WORD
# =========================
def is_bad(text: str) -> bool:
    clean = normalize(text)
    return any(word in clean for word in BAD_WORDS)


@router.message(UploadState.wait_title)
async def input_title(message: Message, state: FSMContext):

    async with user_lock(message.from_user.id):

        title = (message.text or "").strip()

        # =========================
        # SKIP
        # =========================
        if title.lower() == "/skip":
            title = "Untitled"

        # =========================
        # VALIDASI PANJANG
        # =========================
        elif len(title) < 3:
            return await message.answer("❌ Judul minimal 3 karakter.")

        # =========================
        # FILTER KONTEN TERLARANG 🔥
        # =========================
        if is_bad(title):
            return await message.answer(
                "❌ Judul mengandung kata terlarang.\n"
                "Silakan gunakan judul lain."
            )

        # =========================
        # SAVE
        # =========================
        await state.update_data(title=title)

        # =========================
        # LANJUT PILIH TIPE
        # =========================
        kb = InlineKeyboardBuilder()
        kb.button(text="🆓 Free", callback_data="file_free")
        kb.button(text="💰 Paid", callback_data="file_paid")
        kb.adjust(2)

        await message.answer(
            "💎 Pilih tipe file:",
            reply_markup=kb.as_markup()
        )
# =========================
# SHARE HANDLER
# =========================
@router.callback_query(F.data.startswith("share_"))
async def handle_share(call: CallbackQuery, state: FSMContext):

    await call.answer()

    async with user_lock(call.from_user.id):

        share_media = call.data == "share_yes"

        await state.update_data(
            share_media=share_media
        )

        await state.set_state(UploadState.wait_title)

        try:
            await call.message.edit_text(
                "📝 <b>Masukkan Judul File</b>\n\n"
                "Ketik /skip untuk otomatis.",
                parse_mode="HTML"
            )
        except:
            # fallback kalau gagal edit
            await call.message.answer(
                "📝 <b>Masukkan Judul File</b>\n\n"
                "Ketik /skip untuk otomatis.",
                parse_mode="HTML"
            )


# =========================
# FILE PAID
# =========================
@router.callback_query(F.data == "file_paid")
async def file_paid(call: CallbackQuery, state: FSMContext):

    await call.answer()

    await state.set_state(UploadState.wait_price)

    await call.message.edit_text(
        "💰 Masukkan harga file (min 1000):"
    )


# =========================
# FILE FREE
# =========================
@router.callback_query(F.data == "file_free")
async def file_free(call: CallbackQuery, state: FSMContext):

    await call.answer()

    async with user_lock(call.from_user.id):  # ✅ TAMBAH INI

        await state.update_data(
            is_paid=False,
            price=0,
            payment_provider=None
        )

        await call.message.edit_text("⏳ Menyimpan file...")

        await finalize_save(call.message, state, call.from_user.id)


# =========================
# INPUT PRICE
# =========================
@router.message(UploadState.wait_price)
async def input_price(message: Message, state: FSMContext):

    async with user_lock(message.from_user.id):  # ✅ TAMBAH INI

        text = (message.text or "").replace(".", "").replace(",", "")

        if not text.isdigit():
            return await message.answer("❌ Harga harus angka.")

        price = int(text)

        if price < 1000:
            return await message.answer("❌ Minimal Rp1000.")

        await state.update_data(
            is_paid=True,
            price=price,
            payment_provider="bayargg"
        )

        await message.answer(f"⏳ Menyimpan file dengan harga Rp{price:,}...")

        await finalize_save(message, state, message.from_user.id)
    
# =========================
# FINAL SAVE
# =========================
async def finalize_save(message: Message, state: FSMContext, user_id: int):

    data = await state.get_data()

    if data.get("saving"):
        return

    await state.update_data(saving=True)

    media = data.get("media", [])

    if not media:
        return await message.answer("❌ No media found")

    # =========================
    # BASIC INFO
    # =========================
    title = data.get("title") or "Untitled File"
    creator = message.from_user.full_name

    # =========================
    # SETTINGS
    # =========================
    share_media = data.get("share_media", True)

    is_paid = data.get("is_paid", False)
    price = data.get("price", 0)
    payment_provider = data.get("payment_provider")

    pool = await get_pool()

    # =========================
    # AUTO REGISTER USER
    # =========================
    await pool.execute(
        """
        INSERT INTO users
        (
            id,
            username,
            full_name
        )
        VALUES
        ($1,$2,$3)

        ON CONFLICT (id)
        DO UPDATE SET
            username = EXCLUDED.username,
            full_name = EXCLUDED.full_name
        """,
        user_id,
        message.from_user.username,
        message.from_user.full_name
    )

    # =========================
    # GENERATE UNIQUE CODE
    # =========================
    while True:

        code = "zyxfidxbot" + "".join(
            random.choices(
                string.ascii_uppercase + string.digits,
                k=10
            )
        )

        exists = await pool.fetchval(
            "SELECT 1 FROM files WHERE code=$1",
            code
        )

        if not exists:
            break

    # =========================
    # 🔥 LINK UTAMA & BACKUP
    # =========================
    main_link = f"https://t.me/{BOT_USERNAME}?start=getFile_{code}"
    backup_link = f"https://t.me/{BACKUP_BOT_USERNAME}?start=getFile_{code}"

    # =========================
    # SAVE FILE
    # =========================
    await pool.execute(
        """
        INSERT INTO files
        (
            code,
            title,
            creator,
            media,
            share_media,
            is_share,
            owner_id,
            seller_id,
            media_count,
            expires_at,
            is_paid,
            price,
            payment_provider,
            view_count,
            download_count,
            favorite_count
        )

        VALUES
        (
            $1,$2,$3,$4,$5,$6,
            $7,$8,$9,NULL,
            $10,$11,$12,
            $13,$14,$15
        )
        """,

        code,
        title,
        creator,
        json.dumps(media),

        share_media,
        share_media,

        user_id,
        user_id,

        len(media),

        is_paid,
        price,
        payment_provider,

        0,
        0,
        0
    )

    await state.clear()

    # =========================
    # RESPONSE
    # =========================
    media_mode = (
        f"💰 Media Mode : Paid (Rp {price:,})".replace(",", ".")
        if is_paid
        else "🆓 Media Mode : Free"
    )

    text = (
        "✅ <b>FILE SAVED SUCCESSFULLY</b>\n\n"
        f"📋 Files : {len(media)}\n"
        f"🔑 Code : <code>{code}</code>\n"
        f"{media_mode}\n\n"
        f"🚀 <a href='{backup_link}'>Backup (backup)</a>\n\n"
        f"🔗 Link : {main_link}"
    )

    # =========================
    # 🔥 BUTTON BACKUP
    # =========================
    kb = InlineKeyboardBuilder()
    kb.button(text="🚀 BACKUP", url=backup_link)

    await message.answer(
        text,
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )

    # =========================
    # LOG CHANNEL
    # =========================
    try:

        me = await message.bot.get_me()

        await message.bot.send_message(
            CHANNEL_ID,
            text + f"\n\n🤖 Upload Bot : @{me.username}",
            parse_mode="HTML"
        )

    except Exception:
        pass
