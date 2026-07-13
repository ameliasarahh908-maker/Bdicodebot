import logging
import json
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from states.upload import UploadState
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from utils.force_sub import check_force_sub
from keyboards.menu import home_kb
from keyboards.join import join_kb
from database import execute, fetchrow, fetchval

router = Router()


# =========================
# START (BERSIH)
# =========================
@router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()

    user_id = message.from_user.id
    username = message.from_user.username or "unknown"

    loading = await message.answer(
        "<b><i>⚡ Loading...</i></b>",
        parse_mode="HTML"
    )

    try:
        await process_start(message, loading, user_id, username)
    except Exception as e:
        logging.exception(f"START ERROR: {e}")
        await loading.edit_text(
            "<b><i>❌ SYSTEM ERROR</i></b>",
            parse_mode="HTML"
        )

@router.message(F.photo | F.video | F.document)
async def auto_upload(message: Message, state: FSMContext):

    data = await state.get_data()

    if not data:
        await state.set_state(UploadState.waiting_media)
        await state.update_data(
            media=[],
            video=0,
            photo=0,
            doc=0,
            share=True
        )
        data = await state.get_data()

    media = data["media"]

    item = None

    if message.photo:
        item = {
            "file_id": message.photo[-1].file_id,
            "type": "photo"
        }
        data["photo"] += 1

    elif message.video:
        item = {
            "file_id": message.video.file_id,
            "type": "video"
        }
        data["video"] += 1

    elif message.document:
        item = {
            "file_id": message.document.file_id,
            "type": "document"
        }
        data["doc"] += 1

    if not item:
        return

    media.append(item)

    await state.update_data(**data)

    total = len(media)

    await message.answer(
        (
            "<b><i>✅ MEDIA RECEIVED</i></b>\n\n"
            f"<b><i>📦 Total Media : {total}</i></b>\n"
            f"<b><i>🎥 Videos : {data['video']}</i></b>\n"
            f"<b><i>🖼 Photos : {data['photo']}</i></b>\n"
            f"<b><i>📄 Documents : {data['doc']}</i></b>\n\n"
            "<b><i>Send more media or click DONE when finished.</i></b>"
        ),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ DONE",
                        callback_data="done_upload"
                    )
                ]
            ]
        )
    )

@router.message(UploadState.waiting_media)
async def collect_media(message: Message, state: FSMContext):

    data = await state.get_data()
    media = data["media"]

    item = None

    if message.photo:
        file_id = message.photo[-1].file_id
        item = {"file_id": file_id, "type": "photo"}
        data["photo"] += 1

    elif message.video:
        file_id = message.video.file_id
        item = {"file_id": file_id, "type": "video"}
        data["video"] += 1

    elif message.document:
        file_id = message.document.file_id
        item = {"file_id": file_id, "type": "document"}
        data["doc"] += 1

    if not item:
        return

    media.append(item)

    await state.update_data(**data)

    await message.answer("✅ Media saved")

@router.message(UploadState.waiting_media, F.text)
async def ignore_text_upload(message: Message):
    await message.answer("❌ Kirim media, bukan text")

@router.callback_query(F.data == "done_upload")
async def done_upload(call: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    if not data.get("media"):
        return await call.answer("No media!", show_alert=True)

    await state.set_state(UploadState.choose_share)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📤 SHARE", callback_data="share"),
                InlineKeyboardButton(text="🔒 NO SHARE", callback_data="noshare")
            ]
        ]
    )

    await call.message.answer(
        "<b><i>Choose share setting</i></b>",
        parse_mode="HTML",
        reply_markup=kb
    )

@router.callback_query(F.data.in_(["share", "noshare"]))
async def set_share(call: CallbackQuery, state: FSMContext):

    share = call.data == "share"

    await state.update_data(share=share)

    await state.set_state(UploadState.choose_access)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🆓 FREE", callback_data="free"),
                InlineKeyboardButton(text="💰 PAID", callback_data="paid")
            ]
        ]
    )

    await call.message.answer(
        "<b><i>Select access type</i></b>",
        parse_mode="HTML",
        reply_markup=kb
    )

@router.callback_query(F.data.in_(["free", "paid"]))
async def set_access(call: CallbackQuery, state: FSMContext):

    is_paid = call.data == "paid"

    await state.update_data(is_paid=is_paid)

    if is_paid:
        await state.set_state(UploadState.set_price)
        return await call.message.answer("💰 Send price")

    await state.set_state(UploadState.set_title)
    await call.message.answer("📝 Send title")

@router.message(UploadState.set_price)
async def input_price(message: Message, state: FSMContext):

    if not message.text.isdigit():
        return await message.answer("Invalid price")

    await state.update_data(price=int(message.text))

    await state.set_state(UploadState.set_title)

    await message.answer("📝 Send title")

import random
import string

def random_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))


@router.message(UploadState.set_title)
async def finish_upload(message: Message, state: FSMContext):

    data = await state.get_data()

    title = message.text
    media = data["media"]

    video = data["video"]
    photo = data["photo"]
    doc = data["doc"]

    part1 = random_code()
    part2 = random_code()

    code = f"zyxfidxbot_{part1}_{part2}_{video}v{photo}p{doc}d"
    
    await execute(
        """
        INSERT INTO files (code, title, media, is_paid, price, owner_id, share_media)
        VALUES ($1,$2,$3,$4,$5,$6,$7)
        """,
        code,
        title,
        json.dumps(media),
        data.get("is_paid", False),
        data.get("price", 0),
        message.from_user.id,
        data.get("share", True)
    )

    await state.clear()

    await message.answer(
        f"<b><i>✅ UPLOAD SUCCESS</i></b>\n\n<code>{code}</code>",
        parse_mode="HTML"
    )

# =========================
# HANDLE CODE (NO DEEPLINK)
# =========================
@router.message(F.text)
async def handle_code(message: Message, state: FSMContext):

    # 🔥 penting: kalau lagi upload → skip
    if await state.get_state():
        return

    text = message.text.strip()

    if text.startswith("/"):
        return

    if len(text) < 6:
        return

    code = text

    file = await fetchrow(
        """
        SELECT title, media, share_media, is_paid, price, owner_id
        FROM files
        WHERE code=$1
        """,
        code
    )

    if not file:
        return await message.answer(
            "<b><i>❌ Invalid file code</i></b>",
            parse_mode="HTML"
        )

    media = json.loads(file["media"] or "[]")

    if not media:
        return await message.answer(
            "<b><i>❌ File is empty</i></b>",
            parse_mode="HTML"
        )

    is_paid = file["is_paid"]
    price = file["price"] or 0
    share_media = file.get("share_media", True)
    protect = not share_media
    title=file["title"]

    # =========================
    # CHECK STATUS
    # =========================
    vip = await fetchval(
        """
        SELECT 1 FROM users
        WHERE telegram_id=$1
        AND vip=TRUE
        AND vip_until > NOW()
        """,
        message.from_user.id
    )

    purchased = await fetchval(
        """
        SELECT 1 FROM file_purchases
        WHERE user_id=$1
        AND file_code=$2
        AND status='paid'
        LIMIT 1
        """,
        message.from_user.id,
        code
    )

    owner = message.from_user.id == file["owner_id"]

    mode = f"💰 Paid • Rp {price:,}".replace(",", ".") if is_paid else "🆓 Free"

    caption = (
        "<b><i>📂 ZYXFIDXBOT</i></b>\n\n"
        f"<b><i>📌 TITLE :</i></b> {title}\n"
        f"<b><i>🔑 CODE :</i></b> <code>{code}</code>\n"
        f"<b><i>📦 FILE :</i></b> {len(media)}\n"
        f"<b><i>📂 MODE :</i></b> {mode}\n"
        "<b><i>━━━━━━━━━━━━━━</i></b>"
    )

    # =========================
    # LOCKED
    # =========================
    if is_paid and not vip and not owner and not purchased:

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"💳 Pay Rp {price:,}".replace(",", "."),
                        callback_data=f"buyfile:{code}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="💎 Upgrade VIP",
                        callback_data="vvip"
                    )
                ]
            ]
        )

        return await message.answer(
            caption + "\n\n<b><i>🔒 File is locked</i></b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )

    # =========================
    # SEND FILE
    # =========================
    first = media[0]
    fid = first["file_id"]
    ftype = first.get("type", "document")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📂 OPEN PAGE",
                    callback_data=f"page:{code}:1"
                )
            ]
        ]
    )

    try:
        if ftype == "photo":
            await message.answer_photo(
                fid,
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
                protect_content=protect
            )

        elif ftype == "video":
            await message.answer_video(
                fid,
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
                protect_content=protect
            )

        else:
            await message.answer_document(
                fid,
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
                protect_content=protect
            )

    except Exception as e:
        await message.answer(
            f"<b><i>❌ MEDIA ERROR</i></b>\n\n<code>{e}</code>",
            parse_mode="HTML"
        )


# =========================
# PROCESS START
# =========================
async def process_start(message, loading, user_id, username):

    bot = message.bot

    try:
        sub = await check_force_sub(bot, user_id)
    except:
        sub = True

    if not sub:
        return await loading.edit_text(
            "<b><i>❌ JOIN REQUIRED</i></b>",
            parse_mode="HTML",
            reply_markup=join_kb()
        )

    await execute(
        """
        INSERT INTO users (telegram_id, username, chat_id, balance)
        VALUES ($1,$2,$3,0)
        ON CONFLICT (telegram_id)
        DO UPDATE SET username=EXCLUDED.username, chat_id=EXCLUDED.chat_id
        """,
        user_id,
        username,
        message.chat.id
    )

    user = await fetchrow(
        "SELECT username, balance FROM users WHERE telegram_id=$1",
        user_id
    )

    await render_home_fast(
        bot,
        loading,
        user_id,
        user["username"] or "unknown",
        user["balance"] or 0
    )


# =========================
# HOME UI
# =========================
async def render_home_fast(bot, message, user_id, username, balance):

    user = await fetchrow(
        """
        SELECT vip, vip_until, vvip, vvip_until
        FROM users
        WHERE telegram_id=$1
        """,
        user_id
    )

    status = "FREE"
    expire = "-"

    if user:
        now = datetime.now()

        if user["vvip"] and user["vvip_until"] and user["vvip_until"] > now:
            status = "👑 VVIP"
            expire = user["vvip_until"].strftime("%d-%m-%Y %H:%M")
        elif user["vip"] and user["vip_until"] and user["vip_until"] > now:
            status = "💎 VIP"
            expire = user["vip_until"].strftime("%d-%m-%Y %H:%M")

    text = (
        "<b><i>📂 DECODER FILE BOT</i></b>\n\n"
        f"<b><i>🆔 ID :</i></b> <code>{user_id}</code>\n"
        f"<b><i>👤 Username :</i></b> @{username}\n"
        f"<b><i>💎 Status :</i></b> {status}\n"
        f"<b><i>⏳ Active :</i></b> {expire}\n"
    )

    await message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=home_kb()
    )

