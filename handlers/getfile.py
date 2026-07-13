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
        "*𝐙𝐘𝐗𝐅𝐈𝐃𝐗𝐁𝐎𝐓*\n\n"
        "🔑 *𝐒𝐄𝐍𝐃 𝐘𝐎𝐔𝐑 𝐅𝐈𝐋𝐄 𝐂𝐎𝐃𝐄*\n\n"
        "_Please enter the code to access your file._",
        parse_mode="Markdown"
    )

    await call.answer()
# =========================
# RECEIVE CODE
# =========================
@router.message(GetFileState.wait_code)
async def receive_code(message: Message, state: FSMContext):

    if not message.text:
        return await message.answer("❌ *Invalid code input*")

    import re, time
    from config import CHANNEL_ID

    text = message.text.strip()
    code = None

    m = re.search(r"getFile_([A-Za-z0-9_-]+)", text, re.IGNORECASE)
    if m:
        code = m.group(1)

    if not code:
        m = re.search(r"code\s*[:：]\s*([A-Za-z0-9_-]+)", text, re.IGNORECASE)
        if m:
            code = m.group(1)

    if not code:
        code = text

    pool = await get_pool()

    file = await pool.fetchrow(
        "SELECT * FROM files WHERE code=$1",
        code
    )

    if not file:
        await message.answer("❌ *Code not found*")
        await state.clear()
        return

    # =========================
    # EXPIRE CHECK
    # =========================
    expires_at = file["expires_at"]

    if expires_at and expires_at < int(time.time()):
        await message.answer("❌ *File has expired*")
        await state.clear()
        return

    # =========================
    # VIEW COUNT
    # =========================
    await pool.execute(
        "UPDATE files SET view_count = view_count + 1 WHERE code=$1",
        code
    )

    media = safe_json(file["media"])

    if not media:
        await message.answer("❌ *File is empty*")
        await state.clear()
        return

    # =========================
    # ACCESS CHECK
    # =========================
    is_paid = file["is_paid"] or False
    price = file["price"] or 0

    vip = await pool.fetchval(
        """
        SELECT 1 FROM users
        WHERE telegram_id=$1
        AND vip=TRUE
        AND vip_until > NOW()
        """,
        message.from_user.id
    )

    owner = message.from_user.id == file["owner_id"]

    access = await pool.fetchval(
        """
        SELECT 1 FROM file_purchases
        WHERE user_id=$1
        AND file_code=$2
        AND status='paid'
        """,
        message.from_user.id,
        code
    )

    has_access = bool(vip or owner or access)

    # =========================
    # LOCKED FILE
    # =========================
    if is_paid and not has_access:

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"💳 PAY Rp {price:,}".replace(",", "."),
                        callback_data=f"pay:{code}"
                    )
                ]
            ]
        )

        text_msg = (
            "*🔒 PAID FILE*\n\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"*🔑 CODE:* `{code}`\n\n"
            f"*💰 PRICE:* Rp {price:,}\n\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "_Please complete payment to unlock this file._"
        ).replace(",", ".")

        await message.answer(text_msg, reply_markup=keyboard, parse_mode="Markdown")
        await state.clear()
        return

    # =========================
    # GET FIRST MEDIA (USE MESSAGE_ID)
    # =========================
    first = next((m for m in media if m.get("message_id")), None)

    if not first:
        await message.answer("❌ *Invalid file data (no message_id)*")
        await state.clear()
        return

    msg_id = first["message_id"]

    share_media = file["share_media"] if file["share_media"] is not None else True
    share_status = "PUBLIC" if share_media else "PRIVATE"
    protect = not share_media

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

    caption = (
        "*ZYXFIDXBOT*\n"
        f"*🔑 CODE:* `{code}`\n"
        f"*📊 FILES:* {len(media)}\n"
        f"*📤 ACCESS:* {share_status}"
    )

    try:
        await message.bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=CHANNEL_ID,
            message_id=msg_id,
            caption=caption,
            reply_markup=keyboard,
            protect_content=protect,
            parse_mode="Markdown"
        )

    except Exception as e:
        await message.answer(f"❌ *MEDIA ERROR:*\n`{e}`", parse_mode="Markdown")

    await state.clear()
