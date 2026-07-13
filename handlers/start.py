import logging
import json
from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from states.upload import UploadState
from states import GetFileState
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from utils.force_sub import check_force_sub
from config import CHANNEL_ID
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

@router.message()
async def handle_code(message: Message, state: FSMContext):

    import json

    text = (message.text or "").strip()
    if not text:
        return await message.answer("<b><i>❌ Empty code</i></b>", parse_mode="HTML")

    code = text.split()[0].strip()
    logging.info(f"CHECK FILE CODE: {code}")

    # =========================
    # FETCH FILE
    # =========================
    file = await fetchrow(
        """
        SELECT title, media, share_media, is_paid, price, owner_id
        FROM files
        WHERE code = $1
        LIMIT 1
        """,
        code
    )

    if not file:
        await state.clear()
        return await message.answer("<b><i>❌ File code not found</i></b>", parse_mode="HTML")

    # =========================
    # DATA
    # =========================
    is_paid = file["is_paid"]
    price = file["price"] or 0
    share_media = file["share_media"] if file["share_media"] is not None else True

    protect = not share_media
    title = file["title"] or "Untitled"

    # =========================
    # MEDIA
    # =========================
    try:
        media = json.loads(file["media"]) if file["media"] else []
    except:
        media = []

    if not media:
        await state.clear()
        return await message.answer("<b><i>❌ File is empty</i></b>", parse_mode="HTML")

    # =========================
    # ACCESS CHECK
    # =========================
    user_id = message.from_user.id

    vip = await fetchval(
        """
        SELECT 1 FROM users
        WHERE telegram_id=$1
        AND vip=TRUE
        AND vip_until > NOW()
        """,
        user_id
    )

    purchased = await fetchval(
        """
        SELECT 1 FROM file_purchases
        WHERE user_id=$1
        AND file_code=$2
        AND status='paid'
        """,
        user_id,
        code
    )

    owner = user_id == file["owner_id"]

    if is_paid and not vip and not owner and not purchased:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text=f"💳 Pay Rp {price:,}".replace(",", "."),
                    callback_data=f"buyfile:{code}"
                )
            ]]
        )

        await state.clear()
        return await message.answer(
            "<b><i>🔒 This file is locked (Paid)</i></b>",
            parse_mode="HTML",
            reply_markup=kb
        )

    # =========================
    # CAPTION + BUTTON
    # =========================
    caption = (
        "<b><i>📂 EARNFILEBOX</i></b>\n\n"
        f"<b><i>📌 Title :</i></b> {title}\n"
        f"<b><i>🔑 Code :</i></b> <code>{code}</code>\n"
        f"<b><i>📦 Files :</i></b> {len(media)}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="📂 OPEN PAGE",
                callback_data=f"page:{code}:1"
            )
        ]]
    )

    # =========================
    # SEND MEDIA (COPY ONLY)
    # =========================
    sent = 0

    for item in media:
        message_id = item.get("message_id")

        if not message_id:
            logging.error("SKIP: NO MESSAGE_ID")
            continue

        try:
            await message.bot.copy_message(
                chat_id=message.chat.id,
                from_chat_id=CHANNEL_ID,
                message_id=int(message_id),
                protect_content=protect
            )

            sent += 1

        except Exception as e:
            logging.error(f"COPY ERROR {message_id}: {e}")

    # =========================
    # HEADER (CAPTION DI AKHIR)
    # =========================
    if sent > 0:
        await message.answer(
            caption,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    else:
        await message.answer(
            "<b><i>❌ Failed to send all media</i></b>",
            parse_mode="HTML"
        )

    await state.clear()

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
        now = datetime.now(timezone.utc)

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
        parse_mode="HTML"
    )
