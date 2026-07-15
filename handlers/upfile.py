import asyncio
import json
import random
import string
import time
from typing import Dict

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import CHANNEL_ID, BOT_URL
from config import BACKUP_BOT_URL
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


# =========================
# SAFE EDIT
# =========================
async def safe_update(bot, chat_id, message_id, text, user_id, reply_markup=None):
    if not message_id:
        return

    async with get_lock(user_id):
        now = time.time()
        last = _last_update.get(user_id, 0)

        if now - last < UPDATE_DELAY:
            await asyncio.sleep(UPDATE_DELAY - (now - last))

        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup
            )
            _last_update[user_id] = time.time()

        except TelegramBadRequest:
            pass


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

    async with get_lock(call.from_user.id):

        await state.clear()
        await state.set_state(UploadState.upload)

        if not await check_force_sub(call.bot, call.from_user.id):
            return await call.message.answer(
                "❌ Join channel terlebih dahulu.",
                reply_markup=join_kb()
            )

        msg = await call.message.edit_text("⏳ Loading...")
        await asyncio.sleep(0.2)

        await msg.edit_text(
            "📦 <b>UPLOAD MODE ACTIVE</b>\n\n"
            "📤 Kirim foto, video atau dokumen.\n"
            "Maksimal <b>200 file</b>.\n\n"
            "Jika sudah selesai tekan tombol <b>STOP & SAVE</b>.",
            parse_mode="HTML"
        )

        await state.update_data(
            upload_mode=True,

            # Media
            media=[],

            # Informasi utama
            title=None,

            # Share
            share_media=True,

            # Paid / Free
            is_paid=False,
            price=0,

            # Counter (boleh tetap)
            view_count=0,
            download_count=0,
            favorite_count=0,

            # Progress
            progress_msg_id=msg.message_id,
            saving=False
        )


# =========================
# RECEIVE MEDIA
# =========================
@router.message(F.document | F.video | F.photo)
async def receive_media(message: Message, state: FSMContext):

    async with get_lock(message.from_user.id):

        data = await state.get_data()

        if not data.get("upload_mode"):
            return

        media = data.get("media", [])

        if len(media) >= MAX_MEDIA:
            return await message.answer(
                f"❌ Maksimal {MAX_MEDIA} file."
            )

        # =========================
        # GET FILE INFO
        # =========================
        if message.document:
            file = message.document
            media_type = "document"
            file_name = file.file_name

        elif message.video:
            file = message.video
            media_type = "video"
            file_name = getattr(file, "file_name", None)

        else:
            file = message.photo[-1]
            media_type = "photo"
            file_name = None

        file_id = file.file_id
        file_size = file.file_size

        # =========================
        # DUPLICATE CHECK
        # =========================
        if any(x["file_id"] == file_id for x in media):
            return

        # =========================
        # SAVE
        # =========================
        media.append({
            "file_id": file_id,
            "type": media_type,
            "file_name": file_name,
            "file_size": file_size
        })

        await state.update_data(media=media)

        # =========================
        # DELETE USER MESSAGE
        # =========================
        try:
            await message.delete()
        except:
            pass

        # =========================
        # PROGRESS UI
        # =========================
        total = len(media)

        percent = int((total / MAX_MEDIA) * 100)

        progress = min(10, int((total / MAX_MEDIA) * 10))

        bar = "█" * progress + "░" * (10 - progress)

        text = (
            "📦 <b>UPLOAD MANAGER</b>\n\n"
            f"📁 Total File : <b>{total}</b>\n"
            f"📊 Progress : [{bar}] {percent}%\n"
            f"📥 Maksimal : {MAX_MEDIA}\n\n"
            "Jika semua file sudah terkirim,\n"
            "tekan tombol <b>STOP & SAVE</b>."
        )

        kb = InlineKeyboardBuilder()

        kb.button(
            text="⏹ STOP & SAVE",
            callback_data="save_upfile"
        )

        kb.button(
            text="❌ CANCEL",
            callback_data="cancel_upfile"
        )

        kb.adjust(2)

        await safe_update(
            message.bot,
            message.chat.id,
            data.get("progress_msg_id"),
            text,
            message.from_user.id,
            kb.as_markup()
        )


# =========================
# CANCEL
# =========================
@router.callback_query(F.data == "cancel_upfile")
async def cancel(call: CallbackQuery, state: FSMContext):

    await call.answer()

    async with get_lock(call.from_user.id):

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

    async with get_lock(call.from_user.id):

        data = await state.get_data()

        # reset flag biar gak ke-lock
        await state.update_data(saving=False)

        if data.get("saving"):
            return await call.answer(
                "Sedang diproses...",
                show_alert=True
            )

        if not data.get("media"):
            return await call.answer(
                "Belum ada file.",
                show_alert=True
            )

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
# INPUT TITLE
# =========================
@router.message(UploadState.wait_title)
async def input_title(message: Message, state: FSMContext):

    async with get_lock(message.from_user.id):

        title = (message.text or "").strip()

        # skip dulu baru validasi
        if title.lower() == "/skip":
            title = "Untitled"

        elif len(title) < 3:
            return await message.answer("❌ Judul minimal 3 karakter.")

        await state.update_data(title=title)

        # lanjut ke pilih tipe
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

    async with get_lock(call.from_user.id):

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

    async with get_lock(user_id):

        data = await state.get_data()

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
        # BACKUP BOT LINK
        # =========================
        share_link = (
            f"{BACKUP_BOT_URL}"
            f"?start=getFile_{code}"
        )


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
            f"💰 Media Mode : Paid (Rp {price:,})"
            .replace(",", ".")
            if is_paid
            else
            "🆓 Media Mode : Free"
        )


        text = (
            "✅ <b>FILE SAVED SUCCESSFULLY</b>\n\n"
            f"📋 Files : {len(media)}\n"
            f"🔑 Code : <code>{code}</code>\n"
            f"{media_mode}\n\n"
            f"🔗 Link : {share_link}"
        )


        await message.answer(
            text,
            parse_mode="HTML"
        )


        # =========================
        # LOG CHANNEL
        # =========================
        try:

            me = await message.bot.get_me()

            await message.bot.send_message(
                CHANNEL_ID,
                text +
                f"\n\n🤖 Upload Bot : @{me.username}",
                parse_mode="HTML"
            )

        except Exception:
            pass
