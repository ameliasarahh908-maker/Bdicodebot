import asyncio
import logging
import re

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from utils.force_sub import check_force_sub
from keyboards.menu import home_kb
from keyboards.join import join_kb
from database import get_pool
from utils.user import get_user_status

router = Router()


# =========================
# START
# =========================
@router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()

    user_id = message.from_user.id
    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else message.from_user.full_name
    )

    # =========================
    # DEEP LINK FILE
    # =========================
    args = message.text.split(maxsplit=1)

    if len(args) > 1:
        payload = args[1].strip()

        # FORMAT BARU
        match = re.search(r"Zyx\d{8}File\d{8}", payload, re.IGNORECASE)

        if match:
            code = match.group(0)
            from handlers.getfile import open_file_by_code
            return await open_file_by_code(message, code)

        # FORMAT LAMA
        if payload.startswith("getFile_"):
            code = payload.replace("getFile_", "", 1).strip()
            if code:
                from handlers.getfile import open_file_by_code
                return await open_file_by_code(message, code)

    # =========================
    # NORMAL START
    # =========================
    loading = await message.answer("⚡ Loading...")

    try:
        await process_start(message, loading, user_id, username)
    except Exception as e:
        logging.exception(f"START ERROR: {e}")
        try:
            await loading.edit_text("❌ SYSTEM ERROR")
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
        try:
            await loading.edit_text(
                "❌ *JOIN REQUIRED*\n\n"
                "_Please join all required channels first._",
                reply_markup=join_kb(),
                parse_mode="Markdown"
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        return

    pool = await get_pool()

    # =========================
    # CREATE / UPDATE USER
    # =========================
    await pool.execute(
        """
        INSERT INTO users (user_id, chat_id, username, full_name)
        VALUES ($1,$1,$2,$3)
        ON CONFLICT (user_id)
        DO UPDATE SET
            username = EXCLUDED.username,
            full_name = EXCLUDED.full_name
        """,
        user_id,
        username,
        message.from_user.full_name
    )

    # =========================
    # 🔥 REFERRAL SYSTEM
    # =========================
    args = message.text.split(maxsplit=1)

    if len(args) > 1 and args[1].startswith("ref_"):

        ref_id = args[1].replace("ref_", "", 1)

        if ref_id.isdigit():
            ref_id = int(ref_id)

            if ref_id != user_id:

                existing = await pool.fetchval(
                    "SELECT referred_by FROM users WHERE user_id=$1",
                    user_id
                )

                if not existing:

                    # set referral
                    await pool.execute(
                        "UPDATE users SET referred_by=$1 WHERE user_id=$2",
                        ref_id,
                        user_id
                    )

                    # tambah count
                    await pool.execute(
                        "UPDATE users SET referral_count = referral_count + 1 WHERE user_id=$1",
                        ref_id
                    )

                    total = await pool.fetchval(
                        "SELECT referral_count FROM users WHERE user_id=$1",
                        ref_id
                    )

    # =========================
    # GET USER
    # =========================
    user = await pool.fetchrow(
        "SELECT username FROM users WHERE user_id=$1",
        user_id
    )

    # =========================
    # GET STATUS
    # =========================
    status = await get_user_status(pool, user_id)
    status = (status or "free").lower()

    # =========================
    # OPEN HOME
    # =========================
    await render_home_fast(
        bot,
        loading,
        user_id,
        user["username"] or "unknown",
        status
    )


# =========================
# HOME UI
# =========================
async def render_home_fast(bot, message, user_id, username, status):

    pool = await get_pool()

    bot_username = (await bot.me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    # Saldo
    balance = await pool.fetchval(
        "SELECT balance FROM users WHERE user_id=$1",
        user_id
    ) or 0

    # Total Referral
    referral = await pool.fetchval(
        "SELECT referral_count FROM users WHERE user_id=$1",
        user_id
    ) or 0

    text = f"""
<b>✨ 𝐁𝐎𝐓 𝐌𝐀𝐑𝐊𝐄𝐓 ✨</b>

👤 <b>𝐈𝐃 𝐀𝐊𝐔𝐍</b>
<code>{user_id}</code>

💰 <b>𝐒𝐀𝐋𝐃𝐎</b>
<b>Rp {balance:,.0f}</b>

👥 <b>𝐑𝐄𝐅𝐄𝐑𝐑𝐀𝐋</b>
<b>{referral} Orang</b>

━━━━━━━━━━━━━━━━━━

🔗 <b>𝐋𝐈𝐍𝐊 𝐑𝐄𝐅𝐄𝐑𝐑𝐀𝐋</b>

<code>{ref_link}</code>
"""

    try:
        await message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=await home_kb(user_id),
            disable_web_page_preview=True
        )

    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        raise

    except Exception:
        await bot.send_message(
            user_id,
            text,
            parse_mode="HTML",
            reply_markup=await home_kb(user_id),
            disable_web_page_preview=True
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
        "SELECT username FROM users WHERE user_id=$1",
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
