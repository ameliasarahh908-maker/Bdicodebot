# services/page_service.py
import json
import time

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaDocument
)

from database import get_pool
from utils.media_builder import build_album
from utils.keyboard import build_page_buttons
from services.access_service import check_access
from utils.keyboard import build_page_buttons
from utils.cache import NAV_CACHE

PAGE_SIZE = 10

async def send_page(bot, chat_id, user_id, code, page=1):

    pool = await get_pool()

    file = await pool.fetchrow(
        """
        SELECT *
        FROM files
        WHERE code=$1
        """,
        code
    )

    if not file:
        print("FILE NOT FOUND")
        return False

    # 🔥 pakai access service
    bought = await check_access(pool, user_id, file)

    if not bought:
        print("ACCESS DENIED", user_id, code)
        return False

    # =========================
    # LOAD MEDIA
    # =========================
    media = file["media"]

    if isinstance(media, str):
        try:
            media = json.loads(media)
        except Exception:
            print("MEDIA JSON ERROR")
            return False

    if not isinstance(media, list) or not media:
        print("MEDIA EMPTY")
        return False

    total_page = max(1, (len(media) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(1, min(page, total_page))

    if page == 1:
        await pool.execute(
            """
            UPDATE files
            SET download_count = download_count + 1
            WHERE code=$1
            """,
            code
        )

    chunk = media[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]

    caption = (
        "YZXFIDX\n"
        "━━━━━━━━━━━━━━━\n\n"
        f"🔑 CODE : {code}\n"
        f"📦 PAGE : {page}/{total_page}\n"
        f"📊 TOTAL : {len(media)} FILE"
    )

    protect = not file["share_media"]

    album = []

    for index, item in enumerate(chunk):

        if not isinstance(item, dict):
            continue

        fid = item.get("file_id")
        ftype = (item.get("type") or "document").lower()

        if not fid:
            continue

        cap = caption if index == 0 else None

        if ftype in ("photo", "image"):
            album.append(InputMediaPhoto(media=fid, caption=cap))
        elif ftype == "video":
            album.append(InputMediaVideo(media=fid, caption=cap))
        else:
            album.append(InputMediaDocument(media=fid, caption=cap))

    if not album:
        print("ALBUM EMPTY")
        return False

    try:

        if len(album) == 1:

            item = chunk[0]
            fid = item.get("file_id")
            ftype = (item.get("type") or "document").lower()

            if ftype in ("photo", "image"):
                await bot.send_photo(chat_id, fid, caption=caption, protect_content=protect)
            elif ftype == "video":
                await bot.send_video(chat_id, fid, caption=caption, protect_content=protect)
            else:
                await bot.send_document(chat_id, fid, caption=caption, protect_content=protect)

        else:
            await bot.send_media_group(chat_id, album, protect_content=protect)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                build_page_buttons(code, page, total_page),
                [
                    InlineKeyboardButton(text="📢 Channel Update", url="https://t.me/+F6-XB1gFA9VhMDc1"),
                    InlineKeyboardButton(text="🔔 Notifikasi Code", url="https://t.me/+T8c4gdEWf843ZWQ1")
                ]
            ]
        )

        nav_msg = await bot.send_message(chat_id, "📦 PAGE", reply_markup=keyboard)
        NAV_CACHE[(user_id, code)] = nav_msg.message_id

        return True

    except Exception as e:
        print("SEND MEDIA ERROR", repr(e))
        return False
