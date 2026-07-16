import json

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from utils.user import get_user_status
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
        "🔑 KIRIM KODE FILE"
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

    # =========================
    # AMBIL CODE
    # =========================

    code = None

    m = re.search(
        r"getFile_([A-Za-z0-9_-]+)",
        text,
        re.IGNORECASE
    )

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


    # =========================
    # GET FILE
    # =========================

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



    # =========================
    # EXPIRED CHECK
    # =========================

    expires_at = file["expires_at"]

    if expires_at:

        if hasattr(expires_at, "timestamp"):

            expired = (
                expires_at.timestamp()
                < time.time()
            )

        else:

            expired = (
                expires_at
                < int(time.time())
            )


        if expired:

            await message.answer(
                "❌ File sudah kadaluarsa."
            )

            await state.clear()
            return



    # =========================
    # VIEW COUNT
    # =========================

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

    # =========================
    # 🔥 USER LEVEL (NEW)
    # =========================
    user_level = await get_user_status(message.from_user.id)

    # default type kalau belum ada
    file_type = (file.get("type") or "free").lower()


    if not media:

        await message.answer(
            "❌ FILE KOSONG"
        )

        await state.clear()
        return



    # =========================
    # 🔒 VIP / VVIP ACCESS
    # =========================
    if file_type == "vip":
        if user_level not in ["vip", "vvip"]:
            await message.answer("🔒 File ini khusus VIP")
            await state.clear()
            return

    elif file_type == "vvip":
        if user_level != "vvip":
            await message.answer("👑 File ini khusus VVIP")
            await state.clear()
            return

    is_paid = file["is_paid"] or False
    price = file["price"] or 0


    owner = (
        message.from_user.id
        ==
        file["owner_id"]
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
        owner
        or access
    )


    # =========================
    # PAID LOCK
    # =========================

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
                "Silakan bayar untuk membuka file."
            ).replace(",", "."),
            parse_mode="HTML",
            reply_markup=keyboard
        )


        await state.clear()
        return



    # =========================
    # FREE FILE MENU
    # =========================

    from handlers.open_menu import open_keyboard


    await message.answer(
        (
            "✅ <b>FILE DITEMUKAN</b>\n\n"
            f"📦 Total Media : <b>{len(media)}</b>\n\n"
            "Pilih metode pengiriman:"
        ),
        parse_mode="HTML",
        reply_markup=open_keyboard(code)
    )


    await state.clear()

# =========================
# DEEP LINK HANDLER
# =========================
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

    # =========================
    # 🔥 USER LEVEL (NEW)
    # =========================
    user_level = await get_user_status(message.from_user.id)
    file_type = (file.get("type") or "free").lower()


    if not media:
        return await message.answer(
            "❌ File kosong."
        )


    # =========================
    # EXPIRED CHECK
    # =========================

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


    # =========================
    # 🔒 VIP / VVIP ACCESS
    # =========================
    if file_type == "vip":
        if user_level not in ["vip", "vvip"]:
            return await message.answer("🔒 File ini khusus VIP")

    elif file_type == "vvip":
        if user_level != "vvip":
            return await message.answer("👑 File ini khusus VVIP")

    is_paid = file["is_paid"] or False
    price = file["price"] or 0


    owner = (
        message.from_user.id ==
        file["owner_id"]
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
        owner
        or access
    )


    # =========================
    # PAID FILE
    # =========================

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


        return await message.answer(
            (
                "🔒 <b>FILE BERBAYAR</b>\n\n"
                f"🔑 CODE : <code>{code}</code>\n"
                f"💰 HARGA : Rp {price:,}\n\n"
                "Silakan lakukan pembayaran untuk membuka file."
            ).replace(",", "."),
            parse_mode="HTML",
            reply_markup=keyboard
        )


    # =========================
    # FREE FILE MENU
    # =========================

    from handlers.open_menu import open_keyboard


    return await message.answer(
        (
            "✅ <b>FILE DITEMUKAN</b>\n\n"
            f"📦 Total Media : <b>{len(media)}</b>\n\n"
            "Pilih metode pengiriman:"
        ),
        parse_mode="HTML",
        reply_markup=open_keyboard(code)
    )
