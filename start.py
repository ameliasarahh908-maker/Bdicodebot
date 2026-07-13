import logging
import json
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from utils.force_sub import check_force_sub
from keyboards.menu import home_kb
from keyboards.join import join_kb
from database import get_pool

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


# =========================
# HANDLE CODE (NO DEEPLINK)
# =========================
@router.message(F.text)
async def handle_code(message: Message):

    text = message.text.strip()

    if text.startswith("/"):
        return

    if len(text) < 6:
        return

    code = text

    pool = await get_pool()

    file = await pool.fetchrow(
        """
        SELECT media, share_media, is_paid, price, owner_id
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

    # =========================
    # CHECK STATUS
    # =========================
    vip = await pool.fetchval(
        """
        SELECT 1 FROM users
        WHERE telegram_id=$1
        AND vip=TRUE
        AND vip_until > NOW()
        """,
        message.from_user.id
    )

    purchased = await pool.fetchval(
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
        "<b><i>📂 EARNFILEBOX</i></b>\n\n"
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

    pool = await get_pool()

    await pool.execute(
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

    user = await pool.fetchrow(
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

    pool = await get_pool()

    user = await pool.fetchrow(
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
