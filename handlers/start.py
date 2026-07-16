import asyncio
import logging

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards.language import language_kb
from utils.language import translate
from utils.force_sub import check_force_sub
from keyboards.menu import home_kb
from keyboards.join import join_kb
from database import get_pool

from datetime import datetime

router = Router()


# =========================
# START
# =========================
# =========================
# START
# =========================
@router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):

    await state.clear()

    user_id = message.from_user.id
    username = message.from_user.username or "unknown"


    # =========================
    # DEEP LINK FILE
    # =========================

    args = message.text.split(maxsplit=1)

    if len(args) > 1:

        payload = args[1].strip()


        if payload.startswith("getFile_"):

            code = payload.replace(
                "getFile_",
                "",
                1
            ).strip()


            if code:

                from handlers.getfile import open_file_by_code

                return await open_file_by_code(
                    message,
                    code
                )


    # =========================
    # NORMAL START
    # =========================

    loading = await message.answer(
        "⚡ Loading..."
    )


    try:

        await process_start(
            message,
            loading,
            user_id,
            username
        )


    except Exception as e:

        logging.exception(
            f"START ERROR: {e}"
        )


        try:
            await loading.edit_text(
                "❌ SYSTEM ERROR"
            )

        except:
            pass


# =========================
# PROCESS START
# =========================
async def process_start(message, loading, user_id, username):

    bot = message.bot

    # FORCE SUB CHECK
    try:
        sub = await check_force_sub(bot, user_id)
    except Exception:
        sub = True

    if not sub:
        return await loading.edit_text(
            "❌ *JOIN REQUIRED*\n\n"
            "_Please join all required channels first._",
            reply_markup=join_kb(),
            parse_mode="Markdown"
        )

    pool = await get_pool()

    # CREATE / UPDATE USER
    await pool.execute(
        """
        INSERT INTO users (telegram_id, username, chat_id, balance, language)
        VALUES ($1,$2,$3,0,NULL)
        ON CONFLICT (telegram_id)
        DO UPDATE SET
            username = EXCLUDED.username,
            chat_id = EXCLUDED.chat_id
        """,
        user_id,
        username,
        message.chat.id
    )

    # GET USER
    user = await pool.fetchrow(
        "SELECT username, language FROM users WHERE telegram_id=$1",
        user_id
    )

    # GET STATUS
    status = await get_user_status(pool, user_id)

    # FIRST TIME LANGUAGE
    if not user["language"]:
        await loading.edit_text(
            "*𝐙𝐘𝐗𝐅𝐈𝐃𝐗𝐁𝐎𝐓*\n\n"
            "🌐 *SELECT LANGUAGE*\n\n"
            "_Choose your preferred language._",
            reply_markup=language_kb,
            parse_mode="Markdown"
        )
        return

    # OPEN HOME
    await render_home_fast(
        bot,
        loading,
        user_id,
        user["username"] or "unknown",
        status
    )


# =========================
# GET STATUS FUNCTION
# =========================
async def get_user_status(pool, user_id):

    vip_data = await pool.fetchrow(
        "SELECT vip, vvip, vip_until, vvip_until FROM users WHERE telegram_id=$1",
        user_id
    )

    import pytz
    wib = pytz.timezone("Asia/Jakarta")
    now = datetime.now(wib)

    if not vip_data:
        return "🆓 FREE"

    # =========================
    # FIX TIMEZONE
    # =========================
    vvip_until = vip_data["vvip_until"]
    vip_until = vip_data["vip_until"]

    if vvip_until and vvip_until.tzinfo is None:
        vvip_until = wib.localize(vvip_until)

    if vip_until and vip_until.tzinfo is None:
        vip_until = wib.localize(vip_until)

    # =========================
    # PRIORITY CHECK
    # =========================
    if vip_data["vvip"] and vvip_until and vvip_until > now:
        return "👑 VVIP"

    if vip_data["vip"] and vip_until and vip_until > now:
        return "🔥 VIP"

    return "🆓 FREE"


# =========================
# SET LANGUAGE
# =========================
@router.callback_query(F.data.startswith("setlang:"))
async def set_language(call: CallbackQuery):

    lang = call.data.split(":")[1]
    pool = await get_pool()

    await pool.execute(
        "UPDATE users SET language=$1 WHERE telegram_id=$2",
        lang,
        call.from_user.id
    )

    await call.message.edit_text(
        translate(lang, "welcome"),
        parse_mode="Markdown"
    )

    # reload status
    status = await get_user_status(pool, call.from_user.id)

    await render_home_fast(
        call.bot,
        call.message,
        call.from_user.id,
        call.from_user.username or "unknown",
        status
    )

    await call.answer()


# =========================
# HOME UI
# =========================
async def render_home_fast(
    bot,
    message,
    user_id,
    username,
    status
):

    pool = await get_pool()

    lang = await pool.fetchval(
        "SELECT language FROM users WHERE telegram_id=$1",
        user_id
    )

    lang = lang or "en"

    if lang == "id":
        text = (
            "<b>✨ 𝐙𝐘𝐗𝐅𝐈𝐃𝐗𝐁𝐎𝐓 ✨</b>\n\n"
            "📦 Selamat datang di bot penyimpanan file.\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID : <code>{user_id}</code>\n"
            f"👤 Username : @{username}\n"
            f"💎 Status : <b>{status}</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "👇 Silakan pilih menu di bawah."
        )
    else:
        text = (
            "<b>✨ 𝐙𝐘𝐗𝐅𝐈𝐃𝐗𝐁𝐎𝐓 ✨</b>\n\n"
            "📦 Welcome to our file storage bot.\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID : <code>{user_id}</code>\n"
            f"👤 Username : @{username}\n"
            f"💎 Status : <b>{status}</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "👇 Please choose a menu below."
        )

    try:
        await message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=await home_kb(user_id)
        )
    except Exception:
        await bot.send_message(
            user_id,
            text,
            parse_mode="HTML",
            reply_markup=await home_kb(user_id)
        )


# =========================
# CALLBACK HOME
# =========================
@router.callback_query(F.data == "home")
async def back_home(call: CallbackQuery, state: FSMContext):

    await state.clear()
    user_id = call.from_user.id

    try:
        ok = await check_force_sub(call.bot, user_id)
    except Exception:
        ok = True

    if not ok:
        await call.message.answer(
            "❌ JOIN REQUIRED",
            reply_markup=join_kb()
        )
        return await call.answer()

    pool = await get_pool()

    user = await pool.fetchrow(
        "SELECT username FROM users WHERE telegram_id=$1",
        user_id
    )

    status = await get_user_status(pool, user_id)

    await render_home_fast(
        call.bot,
        call.message,
        user_id,
        user["username"] or "unknown",
        status
    )

    await call.answer()
