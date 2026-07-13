import asyncio
import logging
import json

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InputMediaDocument
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.language import language_kb
from utils.language import translate
from utils.force_sub import check_force_sub
from keyboards.menu import home_kb
from keyboards.join import join_kb
from database import get_pool

router = Router()


# =========================
# START (NORMAL + DEEP LINK)
# =========================
@router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    args = message.text.split(maxsplit=1)

    # =========================
    # HANDLE DEEP LINK FILE
    # =========================
    if len(args) > 1:
        payload = args[1]

        if payload.startswith("getFile_"):
            code = payload.replace("getFile_", "")

            pool = await get_pool()

            file = await pool.fetchrow(
                """
                SELECT
                    media,
                    share_media,
                    is_paid,
                    price,
                    payment_provider,
                    owner_id
                FROM files
                WHERE code=$1
                """,
                code
            )

            if not file:
                return await message.answer("❌ File tidak ditemukan")

            media = json.loads(file["media"] or "[]")

            if not media:
                return await message.answer("❌ File kosong")

            is_paid = file["is_paid"]
            price = file["price"] or 0
            share_media = file["share_media"] if file["share_media"] is not None else True
            protect = not share_media

            # =========================
            # CEK VIP + OWNER + PURCHASE
            # =========================
            vip = await pool.fetchval(
                """
                SELECT 1
                FROM users
                WHERE telegram_id=$1
                  AND vip=TRUE
                  AND vip_until > NOW()
                """,
                message.from_user.id
            )

            purchased = await pool.fetchval(
                """
                SELECT 1
                FROM file_purchases
                WHERE user_id=$1
                  AND file_code=$2
                  AND status='paid'
                LIMIT 1
                """,
                message.from_user.id,
                code
            )

            owner = message.from_user.id == file["owner_id"]

            mode = (
                f"💰 Paid • Rp {price:,}".replace(",", ".")
                if is_paid
                else "🆓 Free"
            )

            caption = (
                "*𝐙𝐘𝐗𝐅𝐈𝐃𝐗𝐁𝐎𝐓*\n\n"
                f"🔑 CODE : {code}\n"
                f"📦 FILE : {len(media)}\n"
                f"📂 MODE : {mode}\n"
                "━━━━━━━━━━━━━━\n"
                "Upgrade VIP atau lanjut pembayaran untuk membuka file."
            )


            # =========================
            # FILE BERBAYAR
            # =========================

            if is_paid and not vip and not owner and not purchased:

                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text=f"💳 Bayar Rp {price:,}".replace(",", "."),
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


                await message.answer(
                    caption,
                    reply_markup=keyboard
                )

                return


            # =========================
            # SUDAH BELI / VIP / OWNER
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
                        reply_markup=keyboard,
                        protect_content=protect
                    )

                elif ftype == "video":
                    await message.answer_video(
                        fid,
                        caption=caption,
                        reply_markup=keyboard,
                        protect_content=protect
                    )

                else:
                    await message.answer_document(
                        fid,
                        caption=caption,
                        reply_markup=keyboard,
                        protect_content=protect
                    )

            except Exception as e:
                await message.answer(
                    f"❌ ERROR MEDIA\n\n<code>{e}</code>",
                    parse_mode="HTML"
                )

            return

    # =========================
    # NORMAL START
    # =========================
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    loading = await message.answer("⚡ Loading...")

    try:
        await process_start(
            message,
            loading,
            user_id,
            username
        )
    except Exception as e:
        logging.exception(f"START ERROR: {e}")
        await loading.edit_text("❌ SYSTEM ERROR START")


# =========================
# PROCESS START
# =========================
async def process_start(message, loading, user_id, username):

    bot = message.bot

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


    # =========================
    # CREATE / UPDATE USER
    # =========================

    await pool.execute(
        """
        INSERT INTO users
        (
            telegram_id,
            username,
            chat_id,
            balance,
            language
        )
        VALUES
        ($1,$2,$3,0,NULL)

        ON CONFLICT (telegram_id)
        DO UPDATE SET
            username = EXCLUDED.username,
            chat_id = EXCLUDED.chat_id
        """,
        user_id,
        username,
        message.chat.id
    )


    # =========================
    # GET USER DATA
    # =========================

    user = await pool.fetchrow(
        """
        SELECT 
            username,
            balance,
            language
        FROM users
        WHERE telegram_id=$1
        """,
        user_id
    )


    # =========================
    # FIRST TIME LANGUAGE
    # =========================

    if not user["language"]:

        await loading.edit_text(
            "*𝐙𝐘𝐗𝐅𝐈𝐃𝐗𝐁𝐎𝐓*\n\n"
            "🌐 *SELECT LANGUAGE*\n\n"
            "_Choose your preferred language._",
            reply_markup=language_kb,
            parse_mode="Markdown"
        )

        return


    # =========================
    # OPEN HOME
    # =========================

    await render_home_fast(
        bot,
        loading,
        user_id,
        user["username"] or "unknown",
        user["balance"] or 0
    )
# =========================
# SET LANGUAGE
# =========================

@router.callback_query(F.data.startswith("setlang:"))
async def set_language(call: CallbackQuery):

    lang = call.data.split(":")[1]

    pool = await get_pool()

    await pool.execute(
        """
        UPDATE users
        SET language=$1
        WHERE telegram_id=$2
        """,
        lang,
        call.from_user.id
    )


    await call.message.edit_text(
        translate(lang, "welcome"),
        parse_mode="Markdown"
    )


    await call.message.answer(
        translate(lang, "menu"),
        reply_markup=await home_kb(call.from_user.id),
        parse_mode="Markdown"
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
    balance
):

    pool = await get_pool()

    lang = await pool.fetchval(
        """
        SELECT language
        FROM users
        WHERE telegram_id=$1
        """,
        user_id
    )

    lang = lang or "en"


    if lang == "id":

        text = (
            "<b>𝐙𝐘𝐗𝐅𝐈𝐃𝐗𝐁𝐎𝐓</b>\n\n"
            "Selamat datang di bot penyimpanan file.\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID : <code>{user_id}</code>\n"
            f"👤 Username : @{username}\n"
            f"💰 Saldo : <b>Rp {balance:,}</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Silakan pilih menu di bawah."
        )

    else:

        text = (
            "<b>𝐙𝐘𝐗𝐅𝐈𝐃𝐗𝐁𝐎𝐓</b>\n\n"
            "Welcome to our file storage bot.\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID : <code>{user_id}</code>\n"
            f"👤 Username : @{username}\n"
            f"💰 Balance : <b>Rp {balance:,}</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Please choose a menu below."
        )


    text = text.replace(",", ".")


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
        """
        SELECT username, balance
        FROM users
        WHERE telegram_id=$1
        """,
        user_id
    )

    await render_home_fast(
        call.bot,
        call.message,
        user_id,
        user["username"] or "unknown",
        user["balance"] or 0
    )

    await call.answer()
    

# =========================
# BUY FILE
# ========================

@router.callback_query(F.data.startswith("buyfile:"))
async def buy_file(call: CallbackQuery):

    try:
        await call.message.delete()
    except TelegramBadRequest:
        pass

    code = call.data.split(":")[1]

    pool = await get_pool()

    file = await pool.fetchrow(
        """
        SELECT
            owner_id,
            price,
            payment_provider
        FROM files
        WHERE code=$1
        """,
        code
    )

    if not file:
        return await call.answer(
            "❌ File tidak ditemukan",
            show_alert=True
        )

    # Pemilik tidak perlu membeli file sendiri
    if call.from_user.id == file["owner_id"]:
        return await call.answer(
            "Ini file milik kamu.",
            show_alert=True
        )

    # Cek apakah user sudah membeli file
    purchased = await pool.fetchval(
        """
        SELECT 1
        FROM file_purchases
        WHERE user_id=$1
          AND file_code=$2
          AND status='paid'
        LIMIT 1
        """,
        call.from_user.id,
        code
    )

    if purchased:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📂 OPEN FILE",
                        callback_data=f"page:{code}:1"
                    )
                ]
            ]
        )

        await call.message.answer(
            "✅ Kamu sudah membeli file ini.\n\nKlik tombol di bawah untuk membuka file.",
            reply_markup=keyboard
        )

        return await call.answer()

    price = file["price"] or 0

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 Bayar Sekarang",
                    callback_data=f"pay:{code}"
                )
            ]
        ]
    )

    await call.message.answer(
        (
            "💰 <b>FILE BERBAYAR</b>\n\n"
            f"Harga : <b>Rp {price:,}</b>\n\n"
            "Tekan tombol di bawah untuk membeli."
        ).replace(",", "."),
        parse_mode="HTML",
        reply_markup=keyboard
    )

    await call.answer()
