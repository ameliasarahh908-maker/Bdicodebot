import asyncio
import json
import logging
import time
import uuid
import re

from typing import Dict
from contextlib import asynccontextmanager

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest, RetryAfter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import (
    CHANNEL_ID,
    STORAGE_CHANNEL_ID,
    BOT_USERNAME,
    ADMIN_IDS,
    VVIP_USERS,
)

from database import get_pool
from keyboards.join import join_kb
from utils.force_sub import check_force_sub


router = Router()

MAX_MEDIA = 200
UPDATE_DELAY = 0.30

logging.basicConfig(level=logging.INFO)

_last_update: Dict[int, float] = {}
_user_locks: Dict[int, asyncio.Lock] = {}

# ============================================
# STORAGE COPY
# ============================================

_copy_lock = asyncio.Lock()


async def copy_to_storage(
    bot,
    from_chat_id: int,
    message_id: int,
):
    """
    Copy media ke Storage Channel.
    Retry otomatis jika Telegram FloodWait.
    """

    async with _copy_lock:

        while True:

            try:

                msg = await bot.copy_message(
                    chat_id=STORAGE_CHANNEL_ID,
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                )

                await asyncio.sleep(0.15)

                return msg

            except RetryAfter as e:

                logging.warning(
                    "FloodWait %ss ketika copy storage.",
                    e.retry_after,
                )

                await asyncio.sleep(e.retry_after + 1)

            except Exception:

                logging.exception(
                    "copy_to_storage gagal"
                )

                raise


# ============================================
# USER LOCK
# ============================================

def get_lock(user_id: int) -> asyncio.Lock:

    lock = _user_locks.get(user_id)

    if lock is None:

        lock = asyncio.Lock()

        _user_locks[user_id] = lock

    return lock


@asynccontextmanager
async def user_lock(user_id: int):

    lock = get_lock(user_id)

    async with lock:

        yield


# ============================================
# SAFE EDIT MESSAGE
# ============================================

async def safe_update(
    bot,
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup=None,
):

    now = time.time()

    last = _last_update.get(chat_id)

    if last is not None:

        if now - last < UPDATE_DELAY:

            return

    _last_update[chat_id] = now

    try:

        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )

    except TelegramBadRequest:

        pass

    except Exception:

        logging.exception(
            "safe_update gagal"
        )


# ============================================
# FILTER JUDUL
# ============================================

BAD_WORDS = {
    "bocil",
    "child",
    "underage",
}


def normalize(text: str) -> str:

    return re.sub(
        r"[^a-z0-9]",
        "",
        text.lower(),
    )


def is_bad(text: str) -> bool:

    clean = normalize(text)

    return any(
        word in clean
        for word in BAD_WORDS
    )


# ============================================
# FSM
# ============================================

class UploadState(StatesGroup):

    upload = State()

    wait_title = State()

    wait_price = State()


# ============================================
# RECEIVE MEDIA
# ============================================

@router.message(F.document | F.video | F.photo)
async def receive_media(
    message: Message,
    state: FSMContext,
):

    user_id = message.from_user.id

    async with user_lock(user_id):

        data = await state.get_data()

        # ========================================
        # START UPLOAD
        # ========================================

        if not data.get("upload_mode"):

            pool = await get_pool()

            user = await pool.fetchrow(
                """
                SELECT
                    vvip,
                    vvip_until
                FROM users
                WHERE chat_id=$1
                """,
                user_id,
            )

            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)

            is_admin = user_id in ADMIN_IDS

            vvip = False
            vvip_until = None

            if user:
                vvip = user["vvip"]
                vvip_until = user["vvip_until"]

            if (
                vvip_until
                and vvip_until.tzinfo is None
            ):
                vvip_until = vvip_until.replace(
                    tzinfo=timezone.utc
                )

            is_vvip_active = (
                vvip
                and vvip_until
                and vvip_until > now
            )

            is_vvip = (
                user_id in VVIP_USERS
                or is_vvip_active
            )

            if not (is_admin or is_vvip):

                return await message.answer(
                    "🚫 <b>AKSES DITOLAK</b>\n\n"
                    "📦 Upload hanya untuk:\n"
                    "👑 Admin & VVIP\n\n"
                    "💎 Upgrade ke VVIP agar dapat upload.",
                    parse_mode="HTML",
                )

            if not await check_force_sub(
                message.bot,
                user_id,
            ):

                return await message.answer(
                    "❌ Silakan join channel terlebih dahulu.",
                    reply_markup=join_kb(),
                )

            await state.clear()

            await state.set_state(
                UploadState.upload
            )

            progress = await message.answer(
                "📦 <b>UPLOAD DIMULAI</b>\n\n"
                "Kirim media sebanyak yang diinginkan.\n"
                "Tekan <b>STOP & SAVE</b> jika sudah selesai.",
                parse_mode="HTML",
            )

            await state.update_data(
                upload_mode=True,
                media=[],
                title=None,
                share_media=True,
                is_paid=False,
                price=0,
                payment_provider=None,
                progress_msg_id=progress.message_id,
                saving=False,
            )

            return

        # ========================================
        # DATA MEDIA
        # ========================================

        media = data.get("media", [])

        if len(media) >= MAX_MEDIA:

            return await message.answer(
                f"❌ Maksimal {MAX_MEDIA} file."
            )

        # ========================================
        # COPY KE STORAGE
        # ========================================

        try:

            copied = await copy_to_storage(
                message.bot,
                message.chat.id,
                message.message_id,
            )

            storage_message_id = copied.message_id

        except Exception:

            return await message.answer(
                "⚠️ Storage sedang sibuk.\n"
                "Silakan kirim ulang beberapa detik lagi."
            )

        # ========================================
        # DETEKSI TIPE MEDIA
        # ========================================

        if message.document:

            media_type = "document"

            file_id = message.document.file_id

            file_name = message.document.file_name

            file_size = (
                message.document.file_size or 0
            )

        elif message.video:

            media_type = "video"

            file_id = message.video.file_id

            file_name = getattr(
                message.video,
                "file_name",
                None,
            )

            file_size = (
                message.video.file_size or 0
            )

        else:

            media_type = "photo"

            file_id = message.photo[-1].file_id

            file_name = None

            file_size = (
                message.photo[-1].file_size or 0
            )

        # ========================================
        # DUPLIKAT
        # ========================================

        duplicate = any(

            item["file_id"] == file_id
            or item["message_id"] == storage_message_id

            for item in media
        )

        if duplicate:

            return

        # ========================================
        # SIMPAN MEDIA
        # ========================================

        media.append(
            {
                "message_id": storage_message_id,
                "file_id": file_id,
                "type": media_type,
                "file_name": file_name,
                "file_size": file_size,
            }
        )

        await state.update_data(
            media=media
        )

        # ========================================
        # HAPUS CHAT USER
        # ========================================

        try:
            await message.delete()
        except Exception:
            pass

        # ========================================
        # UPDATE PROGRESS
        # ========================================

        text = (
            "📦 <b>UPLOAD MODE</b>\n\n"
            f"📁 Total File : "
            f"<b>{len(media)}/{MAX_MEDIA}</b>\n\n"
            "Jika selesai tekan tombol di bawah."
        )

        kb = InlineKeyboardBuilder()

        kb.button(
            text="⏹ STOP & SAVE",
            callback_data="save_upfile",
        )

        kb.button(
            text="❌ BATAL",
            callback_data="cancel_upfile",
        )

        kb.adjust(1)

        progress_msg = data.get(
            "progress_msg_id"
        )

        if progress_msg:

            await safe_update(
                message.bot,
                message.chat.id,
                progress_msg,
                text,
                kb.as_markup(),
            )


# ============================================
# CANCEL UPLOAD
# ============================================

@router.callback_query(F.data == "cancel_upfile")
async def cancel_upload(
    call: CallbackQuery,
    state: FSMContext,
):

    await call.answer()

    async with user_lock(call.from_user.id):

        data = await state.get_data()

        progress_msg = data.get("progress_msg_id")

        if progress_msg:

            try:

                await call.bot.delete_message(
                    chat_id=call.message.chat.id,
                    message_id=progress_msg,
                )

            except Exception:
                pass

        try:

            await call.message.edit_text(
                "❌ <b>UPLOAD DIBATALKAN</b>",
                parse_mode="HTML",
            )

        except Exception:
            pass

        await state.clear()


# ============================================
# STOP & SAVE
# ============================================

@router.callback_query(F.data == "save_upfile")
async def choose_share_mode(
    call: CallbackQuery,
    state: FSMContext,
):

    await call.answer()

    async with user_lock(call.from_user.id):

        data = await state.get_data()

        media = data.get("media", [])

        if not media:

            return await call.answer(
                "Belum ada file.",
                show_alert=True,
            )

        kb = InlineKeyboardBuilder()

        kb.button(
            text="🔗 SHARE MEDIA",
            callback_data="share_yes",
        )

        kb.button(
            text="🔒 PRIVATE",
            callback_data="share_no",
        )

        kb.adjust(2)

        await call.message.edit_text(
            "📦 <b>PILIH MODE FILE</b>\n\n"
            "🔗 Share Media = File dapat dibagikan.\n"
            "🔒 Private = File hanya dapat diakses menggunakan kode.",
            parse_mode="HTML",
            reply_markup=kb.as_markup(),
        )


# ============================================
# SHARE HANDLER
# ============================================

@router.callback_query(F.data.startswith("share_"))
async def share_handler(
    call: CallbackQuery,
    state: FSMContext,
):

    await call.answer()

    async with user_lock(call.from_user.id):

        share_media = (
            call.data == "share_yes"
        )

        await state.update_data(
            share_media=share_media
        )

        await state.set_state(
            UploadState.wait_title
        )

        text = (
            "📝 <b>Masukkan Judul File</b>\n\n"
            "Ketik /skip untuk menggunakan judul otomatis."
        )

        try:

            await call.message.edit_text(
                text,
                parse_mode="HTML",
            )

        except Exception:

            await call.message.answer(
                text,
                parse_mode="HTML",
            )


# ============================================
# INPUT TITLE
# ============================================

@router.message(UploadState.wait_title)
async def input_title(
    message: Message,
    state: FSMContext,
):

    async with user_lock(message.from_user.id):

        title = (
            message.text or ""
        ).strip()

        if title.lower() == "/skip":

            title = "Untitled"

        else:

            if len(title) < 3:

                return await message.answer(
                    "❌ Judul minimal 3 karakter."
                )

            if is_bad(title):

                return await message.answer(
                    "❌ Judul mengandung kata terlarang.\n"
                    "Silakan gunakan judul lain."
                )

        await state.update_data(
            title=title
        )

        kb = InlineKeyboardBuilder()

        kb.button(
            text="🆓 FREE",
            callback_data="file_free",
        )

        kb.button(
            text="💰 PAID",
            callback_data="file_paid",
        )

        kb.adjust(2)

        await message.answer(
            "💎 <b>Pilih tipe file</b>",
            parse_mode="HTML",
            reply_markup=kb.as_markup(),
        )

# ============================================
# FILE FREE
# ============================================

@router.callback_query(F.data == "file_free")
async def file_free(
    call: CallbackQuery,
    state: FSMContext,
):

    await call.answer()

    async with user_lock(call.from_user.id):

        await state.update_data(
            is_paid=False,
            price=0,
            payment_provider=None,
        )

        try:

            await call.message.edit_text(
                "⏳ <b>Menyimpan file...</b>",
                parse_mode="HTML",
            )

        except Exception:
            pass

        await finalize_save(
            call.message,
            state,
            call.from_user.id,
        )


# ============================================
# FILE PAID
# ============================================

@router.callback_query(F.data == "file_paid")
async def file_paid(
    call: CallbackQuery,
    state: FSMContext,
):

    await call.answer()

    await state.set_state(
        UploadState.wait_price
    )

    await call.message.edit_text(
        "💰 <b>Masukkan harga file</b>\n\n"
        "Minimal Rp1.000",
        parse_mode="HTML",
    )


# ============================================
# INPUT PRICE
# ============================================

@router.message(UploadState.wait_price)
async def input_price(
    message: Message,
    state: FSMContext,
):

    async with user_lock(message.from_user.id):

        text = (
            message.text or ""
        ).replace(".", "").replace(",", "").strip()

        if not text.isdigit():

            return await message.answer(
                "❌ Harga harus berupa angka."
            )

        price = int(text)

        if price < 1000:

            return await message.answer(
                "❌ Harga minimal Rp1.000."
            )

        await state.update_data(
            is_paid=True,
            price=price,
            payment_provider="bayargg",
        )

        await message.answer(
            f"⏳ <b>Menyimpan file...</b>\n\n"
            f"💰 Harga : Rp{price:,}".replace(",", "."),
            parse_mode="HTML",
        )

        await finalize_save(
            message,
            state,
            message.from_user.id,
        )

        
# ============================================
# FINAL SAVE
# ============================================

async def finalize_save(
    message: Message,
    state: FSMContext,
    user_id: int,
):

    data = await state.get_data()

    if data.get("saving"):

        return

    await state.update_data(
        saving=True
    )

    try:

        # ====================================
        # MEDIA
        # ====================================

        media = [

            item

            for item in data.get("media", [])

            if (
                item.get("message_id")
                and item.get("file_id")
            )

        ]

        if not media:

            await state.update_data(
                saving=False
            )

            return await message.answer(
                "❌ Tidak ada file yang dapat disimpan."
            )

        # ====================================
        # DATA
        # ====================================

        title = (
            data.get("title")
            or "Untitled File"
        )

        creator = message.from_user.full_name

        share_media = data.get(
            "share_media",
            True,
        )

        is_paid = data.get(
            "is_paid",
            False,
        )

        price = data.get(
            "price",
            0,
        )

        payment_provider = data.get(
            "payment_provider"
        )

        pool = await get_pool()

        # ====================================
        # UPDATE USER
        # ====================================

        await pool.execute(
            """
            INSERT INTO users(
                chat_id,
                username,
                full_name
            )

            VALUES(
                $1,
                $2,
                $3
            )

            ON CONFLICT(chat_id)

            DO UPDATE SET

                username=EXCLUDED.username,

                full_name=EXCLUDED.full_name
            """,

            user_id,

            message.from_user.username,

            message.from_user.full_name,
        )

        # ====================================
        # GENERATE CODE
        # ====================================

        code = (
            "Zyx"
            + uuid.uuid4().hex[:12]
        )

        main_link = (
            f"https://t.me/{BOT_USERNAME}"
            f"?start=getFile_{code}"
        )

        media_json = json.dumps(
            media,
            ensure_ascii=False,
        )

        media_count = len(media)



        # ====================================
        # SAVE FILE
        # ====================================

        await pool.execute(
            """
            INSERT INTO files(
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

            VALUES(
                $1,
                $2,
                $3,
                $4,
                $5,
                $6,
                $7,
                $8,
                $9,
                NULL,
                $10,
                $11,
                $12,
                0,
                0,
                0
            )
            """,

            code,
            title,
            creator,
            media_json,
            share_media,
            share_media,
            user_id,
            user_id,
            media_count,
            is_paid,
            price,
            payment_provider,
        )

        # ====================================
        # SAVE MEDIA TABLE
        # ====================================

        values = []

        for item in media:

            values.append(
                (
                    code,
                    int(item["message_id"]),
                    item["file_id"],
                    item["type"],
                    item.get("file_size", 0),
                    title,
                )
            )

        if values:

            await pool.executemany(
                """
                INSERT INTO medias(
                    code,
                    message_id,
                    file_id,
                    file_type,
                    file_size,
                    title
                )

                VALUES(
                    $1,
                    $2,
                    $3,
                    $4,
                    $5,
                    $6
                )
                """,
                values,
            )

        # ====================================
        # CLEAR STATE
        # ====================================

        await state.clear()

        # ====================================
        # FILE INFO
        # ====================================

        video_count = sum(
            1
            for x in media
            if x["type"] == "video"
        )

        photo_count = sum(
            1
            for x in media
            if x["type"] == "photo"
        )

        document_count = sum(
            1
            for x in media
            if x["type"] == "document"
        )

        files = []

        if video_count:
            files.append(
                f"{video_count} Videos"
            )

        if photo_count:
            files.append(
                f"{photo_count} Photos"
            )

        if document_count:
            files.append(
                f"{document_count} Documents"
            )

        files_info = (
            " • ".join(files)
            if files
            else "0 File"
        )

        media_mode = (
            f"💰 Media Mode : Paid (Rp {price:,})".replace(",", ".")
            if is_paid
            else "🆓 Media Mode : Free"
        )

        # ====================================
        # SUCCESS MESSAGE
        # ====================================

        text = (
            "✅ <b>FILE BERHASIL DISIMPAN</b>\n\n"
            f"📝 Title : <b>{title}</b>\n"
            f"📋 Files : {files_info}\n"
            f"🔑 Code : <code>{code}</code>\n"
            f"{media_mode}\n\n"
            f"🔗 Link : {main_link}"
        )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔗 Open Link",
                        url=main_link,
                    )
                ]
            ]
        )

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=kb,
        )

        # ====================================
        # LOG CHANNEL
        # ====================================

        try:

            me = await message.bot.get_me()

            log_text = (
                text
                + f"\n\n👤 User ID : <code>{user_id}</code>"
                + f"\n🤖 Upload Bot : @{me.username}"
            )

            await message.bot.send_message(
                chat_id=CHANNEL_ID,
                text=log_text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )

        except Exception:

            logging.exception(
                "Gagal mengirim log upload."
            )

    # ====================================
    # ERROR
    # ====================================

    except Exception:

        logging.exception(
            "FINAL SAVE ERROR"
        )

        await state.update_data(
            saving=False
        )

        await message.answer(
            "❌ Terjadi kesalahan saat menyimpan file.\n"
            "Silakan coba lagi beberapa saat."
        )
