import asyncio
import json
import time
from collections import defaultdict

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from database import get_pool
from config import STORAGE_CHANNEL_ID


router = Router()

PAGE_SIZE = 10

SAME_PAGE_COOLDOWN = 3600      # 1 jam
CHANGE_PAGE_COOLDOWN = 30      # 30 detik

USER_LOCK = defaultdict(lambda: asyncio.Lock())

PAGE_CACHE = {}
PAGE_CHANGE = {}
NAV_CACHE = {}

# =========================
# UTIL
# =========================
async def clear_cache_loop():

    while True:

        await asyncio.sleep(3600)

        now = time.time()

        for cache in [PAGE_CACHE, PAGE_CHANGE]:

            remove = []

            for key, value in list(cache.items()):

                if now - value[1] > 7200:
                    remove.append(key)

            for key in remove:
                del cache[key]
                
def clean_file_id(fid):
    return fid.get("file_id") if isinstance(fid, dict) else fid


def normalize_type(ftype):
    return (ftype or "document").lower()


# =========================
# SEND PAGE (REUSABLE CORE)
# =========================
async def send_page(bot, chat_id, user_id, code, page=1):

    pool = await get_pool()

    file = await pool.fetchrow(
        """
        SELECT *
        FROM files
        WHERE code=$1
        LIMIT 1
        """,
        code
    )

    if not file:
        print("FILE NOT FOUND")
        return False


    # =========================
    # LOAD MEDIA
    # =========================

    media = file["media"]

    if isinstance(media, str):
        try:
            media = json.loads(media)
        except:
            return False


    if not media:
        print("MEDIA EMPTY")
        return False



    total_page = (
        len(media) + PAGE_SIZE - 1
    ) // PAGE_SIZE


    page = max(
        1,
        min(page, total_page)
    )


    chunk = media[
        (page-1)*PAGE_SIZE :
        page*PAGE_SIZE
    ]


    if not chunk:
        return False



    share_media = file["share_media"]

    if share_media is None:
        share_media = True


    protect = not share_media



    album = []


    caption = (
        "ZyxFidxBot\n"
        "━━━━━━━━━━━━━━━\n\n"
        f"🔑 CODE : {code}\n"
        f"📦 PAGE : {page}/{total_page}\n"
        f"📊 TOTAL : {len(media)} FILE"
    )


    # =========================
    # BUILD ALBUM 10 MEDIA
    # =========================

    for index, item in enumerate(chunk):

        if not isinstance(item, dict):
            continue


        fid = item.get("file_id")

        if not fid:
            continue


        ftype = (
            item.get("type")
            or "document"
        ).lower()


        cap = caption if index == 0 else None


        if ftype in ("photo","image"):

            album.append(
                InputMediaPhoto(
                    media=fid,
                    caption=cap
                )
            )


        elif ftype == "video":

            album.append(
                InputMediaVideo(
                    media=fid,
                    caption=cap
                )
            )


        else:

            album.append(
                InputMediaDocument(
                    media=fid,
                    caption=cap
                )
            )


    if not album:
        print("ALBUM EMPTY")
        return False



    try:

        # =========================
        # SEND 1 BUBBLE
        # =========================

        if len(album) == 1:

            item = album[0]

            await bot.send_document(
                chat_id,
                item.media,
                caption=caption,
                protect_content=protect
            )


        else:

            await bot.send_media_group(
                chat_id,
                album
            )



        # =========================
        # PAGE BUTTON
        # =========================

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[

                build_page_buttons(
                    code,
                    page,
                    total_page
                ),

                [
                    InlineKeyboardButton(
                        text="📤 OPEN ALL",
                        callback_data=f"all:{code}"
                    )
                ]

            ]
        )


        nav = await bot.send_message(
            chat_id,
            f"📦 PAGE {page}/{total_page}",
            reply_markup=keyboard
        )


        NAV_CACHE[
            (user_id, code)
        ] = nav.message_id


        print(
            "PAGE SENT",
            code,
            page,
            len(album)
        )


        return True



    except Exception as e:

        print(
            "SEND PAGE ERROR",
            e
        )

        return False


# =========================
# BUTTON
# =========================
def build_page_buttons(code: str, page: int, total: int):

    row = []


    # PREV
    if page > 1:
        row.append(
            InlineKeyboardButton(
                text="⬅️ Prev",
                callback_data=f"page:{code}:{page-1}"
            )
        )


    # NOMOR HALAMAN
    start = max(1, page - 2)
    end = min(total, page + 2)

    for i in range(start, end + 1):

        emoji = "🔲" if i == page else (
            "▫️" if i < page else "▪️"
        )

        row.append(
            InlineKeyboardButton(
                text=f"{i}{emoji}",
                callback_data=f"page:{code}:{i}"
            )
        )


    # NEXT
    if page < total:

        row.append(
            InlineKeyboardButton(
                text="Next ➡️",
                callback_data=f"page:{code}:{page+1}"
            )
        )

    else:

        row.append(
            InlineKeyboardButton(
                text="✅ END",
                callback_data="end_page"
            )
        )


    return row


# =========================
# HANDLER
# =========================
@router.callback_query(F.data.startswith("page:"))
async def page_handler(call: CallbackQuery):

    user_id = call.from_user.id

    try:
        await call.answer("📂 Loading...")
    except:
        pass


    try:
        _, code, page = call.data.split(":")
        page = int(page)

    except:
        return



    async with USER_LOCK[user_id]:

        pool = await get_pool()


        file = await pool.fetchrow(
            """
            SELECT *
            FROM files
            WHERE code=$1
            LIMIT 1
            """,
            code
        )


        if not file:

            return await call.answer(
                "❌ File tidak ditemukan",
                show_alert=True
            )



        media = file["media"]

        if isinstance(media, str):

            try:
                media = json.loads(media)

            except:
                media = []



        if not media:

            return await call.answer(
                "❌ Media kosong",
                show_alert=True
            )



        total_page = max(
            1,
            (len(media)+PAGE_SIZE-1)//PAGE_SIZE
        )


        if page > total_page:

            return await call.answer(
                "📄 Halaman habis",
                show_alert=True
            )



        # =========================
        # ACCESS
        # =========================

        access = False


        # FREE
        if not file["is_paid"]:
            access = True


        # OWNER
        elif user_id == file["owner_id"]:
            access = True


        else:

            bought = await pool.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1
                    FROM file_purchases
                    WHERE user_id=$1
                    AND file_code=$2
                    AND status='paid'
                )
                """,
                user_id,
                code
            )


            if bought:
                access = True



        if not access:

            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=f"💳 Bayar Rp {file['price']:,}".replace(",", "."),
                            callback_data=f"pay:{code}"
                        )
                    ]
                ]
            )


            return await call.message.answer(
                "🔒 <b>FILE BERBAYAR</b>\n\n"
                f"💰 Harga : Rp {file['price']:,}",
                parse_mode="HTML",
                reply_markup=kb
            )



        # hapus tombol lama

        old_nav = NAV_CACHE.get(
            (user_id, code)
        )


        if old_nav:

            try:

                await call.bot.delete_message(
                    call.message.chat.id,
                    old_nav
                )

            except:
                pass



        # kirim halaman

        await send_page(
            call.bot,
            call.message.chat.id,
            user_id,
            code,
            page
        )



@router.callback_query(F.data=="end_page")
async def end_page(call: CallbackQuery):

    await call.answer(
        "📄 Semua file sudah ditampilkan.",
        show_alert=True
    )
