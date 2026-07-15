import json

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import get_pool

router = Router()


# =========================
# STATE
# =========================
class GetFileState(StatesGroup):
    wait_code = State()


# =========================
# UTIL
# =========================
def safe_json(data):
    if isinstance(data, str):
        try:
            return json.loads(data)
        except:
            return []
    return data or []


def get_first_media(media):
    return media[0] if isinstance(media, list) and media else None


# =========================
# START
# =========================
@router.callback_query(F.data == "getfile")
async def getfile_start(call: CallbackQuery, state: FSMContext):

    await state.set_state(GetFileState.wait_code)

    await call.message.edit_text(
        "𝗘𝗔𝗥𝗡𝗙𝗜𝗟𝗘𝗕𝗢𝗫\n\n🔑 KIRIM KODE FILE"
    )

    await call.answer()


# =========================
# RECEIVE CODE
# =========================
@router.message(GetFileState.wait_code)
async def receive_code(message: Message, state: FSMContext):

    if not message.text:
        return await message.answer("❌ Kode kosong")

    import re
    import time

    text = message.text.strip()
    code = None

    m = re.search(r"getFile_([A-Za-z0-9_-]+)", text, re.IGNORECASE)

    if m:
        code = m.group(1)

    if not code:
        m = re.search(
            r"code\s*[:：]\s*([A-Za-z0-9_-]+)",
            text,
            re.IGNORECASE
        )

        if m:
            code = m.group(1)

    if not code:
        code = text


    pool = await get_pool()

    file = await pool.fetchrow(
        """
        SELECT *
        FROM files
        WHERE LOWER(code)=LOWER($1)
        LIMIT 1
        """,
        code
    )


    if not file:
        await message.answer(
            "❌ CODE TIDAK DITEMUKAN"
        )
        await state.clear()
        return


    expires_at = file["expires_at"]

    if expires_at:

        if hasattr(expires_at, "timestamp"):
            expired = expires_at.timestamp() < time.time()

        else:
            expired = expires_at < int(time.time())


        if expired:
            await message.answer(
                "❌ File sudah kadaluarsa."
            )
            await state.clear()
            return



    await pool.execute(
        """
        UPDATE files
        SET view_count = view_count + 1
        WHERE code=$1
        """,
        code
    )


    media = safe_json(
        file["media"]
    )


    if not media:

        await message.answer(
            "❌ FILE KOSONG"
        )

        await state.clear()
        return



    # =========================
    # PAYMENT CHECK
    # =========================

    is_paid = file["is_paid"] or False
    price = file["price"] or 0


    owner = (
        message.from_user.id ==
        file["owner_id"]
    )


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


    access = await pool.fetchval(
        """
        SELECT 1
        FROM file_purchases
        WHERE user_id=$1
        AND file_code=$2
        AND status='paid'
        """,
        message.from_user.id,
        code
    )


    has_access = bool(
        owner or vip or access
    )



    if is_paid and not has_access:


        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"💳 BAYAR Rp {price:,}".replace(",", "."),
                        callback_data=f"pay:{code}"
                    )
                ]
            ]
        )


        await message.answer(
            (
                "🔒 <b>FILE BERBAYAR</b>\n\n"
                f"🔑 CODE : <code>{code}</code>\n"
                f"💰 HARGA : Rp {price:,}\n\n"
                "Silakan lakukan pembayaran untuk membuka file."
            ).replace(",", "."),
            parse_mode="HTML",
            reply_markup=keyboard
        )


        await state.clear()
        return



    # =========================
    # SEND FROM STORAGE CHANNEL
    # =========================

    await send_storage_media(
        message,
        media,
        code,
        file
    )


    await state.clear()

async def send_storage_media(
    message: Message,
    media: list,
    code: str,
    file
):

    from config import STORAGE_CHANNEL_ID


    share_media = (
        file["share_media"]
        if file["share_media"] is not None
        else True
    )


    protect = not share_media


    caption = (
        "ZyxFidxBot\n\n"
        f"🔑 CODE : {code}\n"
        f"📦 FILE : {len(media)}"
    )


    for index, item in enumerate(media):

        try:

            sent = await message.bot.copy_message(
                chat_id=message.chat.id,
                from_chat_id=STORAGE_CHANNEL_ID,
                message_id=item["message_id"],
                protect_content=protect
            )


            if index == 0:

                try:

                    await message.bot.edit_message_caption(
                        chat_id=message.chat.id,
                        message_id=sent.message_id,
                        caption=caption
                    )

                except:
                    pass


        except Exception as e:

            await message.answer(
                f"❌ MEDIA ERROR:\n{e}"
            )

            return False


    return True

async def open_file_by_code(
    message: Message,
    code: str
):
    pool = await get_pool()

    file = await pool.fetchrow(
        """
        SELECT *
        FROM files
        WHERE LOWER(code)=LOWER($1)
        LIMIT 1
        """,
        code
    )

    if not file:
        return await message.answer(
            "❌ File tidak ditemukan."
        )


    media = safe_json(
        file["media"]
    )


    if not media:
        return await message.answer(
            "❌ File kosong."
        )


    import time

    expires_at = file["expires_at"]

    if expires_at:

        if hasattr(expires_at, "timestamp"):
            expired = expires_at.timestamp() < time.time()

        else:
            expired = expires_at < int(time.time())


        if expired:
            return await message.answer(
                "❌ File sudah kadaluarsa."
            )


    is_paid = file["is_paid"] or False
    price = file["price"] or 0


    owner = (
        message.from_user.id ==
        file["owner_id"]
    )


    vip = await pool.fetchval(
        """
        SELECT 1
        FROM users
        WHERE telegram_id=$1
        AND vip=true
        AND vip_until > NOW()
        """,
        message.from_user.id
    )


    access = await pool.fetchval(
        """
        SELECT 1
        FROM file_purchases
        WHERE user_id=$1
        AND file_code=$2
        AND status='paid'
        """,
        message.from_user.id,
        code
    )


    if is_paid and not (owner or vip or access):

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"💳 BAYAR Rp {price:,}".replace(",", "."),
                        callback_data=f"pay:{code}"
                    )
                ]
            ]
        )

        return await message.answer(
            (
                "🔒 <b>FILE BERBAYAR</b>\n\n"
                f"🔑 CODE : <code>{code}</code>\n"
                f"💰 HARGA : Rp {price:,}\n\n"
                "Silakan lakukan pembayaran."
            ).replace(",", "."),
            parse_mode="HTML",
            reply_markup=keyboard
        )


    return await send_storage_media(
        message,
        media,
        code,
        file
    )
