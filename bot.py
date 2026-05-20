import os
import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# =========================
# VARIABLES RAILWAY
# =========================
TOKEN = os.getenv("BOT_TOKEN")

CHANNEL_ID = int(
    os.getenv("CHANNEL_ID")
)

FORCE_CHANNEL_LINK = os.getenv(
    "FORCE_CHANNEL_LINK"
)

# =========================
# BOT
# =========================
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher()

# =========================
# USER SESSION
# =========================
user_sessions = {}

# =========================
# CHECK USER JOIN
# =========================
async def is_joined(user_id):

    try:
        member = await bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=user_id
        )

        if member.status in [
            "member",
            "administrator",
            "creator"
        ]:
            return True

    except:
        return False

    return False


# =========================
# START
# =========================
@dp.message(F.text == "/start")
async def start(message: Message):

    joined = await is_joined(
        message.from_user.id
    )

    # BELUM JOIN
    if not joined:

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="JOIN CHANNEL",
                        url=FORCE_CHANNEL_LINK
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="CEK JOIN",
                        callback_data="cek_join"
                    )
                ]
            ]
        )

        return await message.answer(
            "⚠️ Anda harus join channel terlebih dahulu.",
            reply_markup=keyboard
        )

    # SUDAH JOIN
    await message.answer(
        "✅ Bot terbuka silahkan gunakan bot dengan baik 👌"
    )


# =========================
# BUTTON CEK JOIN
# =========================
@dp.callback_query(F.data == "cek_join")
async def cek_join(callback: CallbackQuery):

    joined = await is_joined(
        callback.from_user.id
    )

    # MASIH BELUM JOIN
    if not joined:

        return await callback.answer(
            "⚠️ Anda belum join channel",
            show_alert=True
        )

    # SUDAH JOIN
    await callback.message.delete()

    await callback.message.answer(
        "✅ Bot terbuka silahkan gunakan bot dengan baik 👌"
    )

    await callback.answer()


# =========================
# HANDLE MEDIA
# =========================
@dp.message(
    F.video |
    F.photo |
    F.document
)
async def save_media(message: Message):

    joined = await is_joined(
        message.from_user.id
    )

    # BLOK JIKA BELUM JOIN
    if not joined:
        return

    user_id = message.from_user.id

    # SESSION BARU
    if user_id not in user_sessions:

        user_sessions[user_id] = {
            "videos": [],
            "photos": [],
            "documents": [],
            "notify_msg_id": None
        }

    session = user_sessions[user_id]

    # =========================
    # COPY KE CHANNEL DATABASE
    # =========================
    copied = await bot.copy_message(
        chat_id=CHANNEL_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id
    )

    # =========================
    # SIMPAN MEDIA
    # =========================
    if message.video:
        session["videos"].append(
            copied.message_id
        )

    elif message.photo:
        session["photos"].append(
            copied.message_id
        )

    elif message.document:
        session["documents"].append(
            copied.message_id
        )

    # =========================
    # TOTAL MEDIA
    # =========================
    total_video = len(
        session["videos"]
    )

    total_photo = len(
        session["photos"]
    )

    total_doc = len(
        session["documents"]
    )

    total_all = (
        total_video +
        total_photo +
        total_doc
    )

    # =========================
    # HAPUS NOTIFIKASI LAMA
    # =========================
    if session["notify_msg_id"]:

        try:
            await bot.delete_message(
                chat_id=message.chat.id,
                message_id=session[
                    "notify_msg_id"
                ]
            )

        except:
            pass

    # =========================
    # BUTTON CREATE
    # =========================
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="CREATE",
                    callback_data="create_code"
                )
            ]
        ]
    )

    # =========================
    # KIRIM NOTIFIKASI BARU
    # =========================
    notif = await message.answer(
        f"✅ <b>{total_all} Media Diterima</b>\n\n"

        f"📹 Video : {total_video}\n"
        f"🖼 Photo : {total_photo}\n"
        f"📁 Document : {total_doc}",

        reply_markup=keyboard
    )

    # SIMPAN NOTIF ID
    session["notify_msg_id"] = (
        notif.message_id
    )


# =========================
# BUTTON CREATE
# =========================
@dp.callback_query(
    F.data == "create_code"
)
async def create_code(
    callback: CallbackQuery
):

    await callback.answer()

    user_id = callback.from_user.id

    session = user_sessions.get(user_id)

    if not session:

        return await callback.message.answer(
            "⚠️ Tidak ada media."
        )

    total_video = len(
        session["videos"]
    )

    total_photo = len(
        session["photos"]
    )

    total_doc = len(
        session["documents"]
    )

    # CONTOH CODE SEMENTARA
    code = (
        f"bdicodebot_"
        f"{total_video}v_"
        f"{total_photo}p_"
        f"{total_doc}d"
    )

    await callback.message.answer(
        f"✅ Code berhasil dibuat\n\n"
        f"<code>{code}</code>"
    )


# =========================
# MAIN
# =========================
async def main():

    print("BOT RUNNING...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
