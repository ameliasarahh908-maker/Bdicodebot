import asyncio
import json
import time
from collections import defaultdict

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaDocument
)

from database import get_pool

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

        for cache in [PAGE_CACHE, PAGE_CHANGE, NAV_CACHE]:

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
        """,
        code
    )

    if not file:
        print("FILE NOT FOUND")
        return False


    # =========================
    # ACCESS CHECK
    # =========================

    bought = False

    if not file["is_paid"]:
        bought = True

    elif user_id == file["owner_id"]:
        bought = True

    else:

        bought = bool(
            await pool.fetchval(
                """
                SELECT 1
                FROM file_purchases
                WHERE user_id=$1
                AND file_code=$2
                AND status='paid'
                LIMIT 1
                """,
                user_id,
                code
            )
        )


    if not bought:
        print(
            "ACCESS DENIED",
            user_id,
            code
        )
        return False


    # =========================
    # LOAD MEDIA
    # =========================

    media = file["media"]

    if isinstance(media, str):
        try:
            media = json.loads(media)
        except Exception as e:
            print(
                "MEDIA JSON ERROR",
                e
            )
            return False


    if not isinstance(media, list) or not media:
        print("MEDIA EMPTY")
        return False


    total_page = max(
        1,
        (len(media) + PAGE_SIZE - 1) // PAGE_SIZE
    )


    page = max(
        1,
        min(page, total_page)
    )


    chunk = media[
        (page - 1) * PAGE_SIZE:
        page * PAGE_SIZE
    ]


    if not chunk:
        print("PAGE EMPTY")
        return False



    # =========================
    # COUNTER
    # =========================

    if page == 1:

        await pool.execute(
            """
            UPDATE files
            SET download_count = download_count + 1
            WHERE code=$1
            """,
            code
        )


    share_media = file["share_media"]

    if share_media is None:
        share_media = True


    protect = not share_media



    caption = (
        "𝗘𝗔𝗥𝗡𝗙𝗜𝗟𝗘𝗕𝗢𝗫\n"
        "━━━━━━━━━━━━━━━\n\n"
        f"🔑 CODE : {code}\n"
        f"📦 PAGE : {page}/{total_page}\n"
        f"📊 TOTAL : {len(media)} FILE"
    )


    # =========================
    # SEND PAGE VIA STORAGE
    # =========================

    try:

        sent = 0


        for index, item in enumerate(chunk):

            if not isinstance(item, dict):
                continue


            message_id = item.get(
                "message_id"
            )


            if not message_id:
                continue


            try:

                await bot.copy_message(
                    chat_id=chat_id,
                    from_chat_id=STORAGE_CHANNEL_ID,
                    message_id=message_id,
                    protect_content=protect
                )

                sent += 1


            except Exception as e:

                print(
                    "COPY MEDIA ERROR",
                    message_id,
                    e
                )



        if sent == 0:

            print(
                "NO MEDIA SENT"
            )

            return False



        # =========================
        # NAV BUTTON
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
                ],

                [
                    InlineKeyboardButton(
                        text="📢 Channel Update",
                        url="https://t.me/+F6-XB1gFA9VhMDc1"
                    ),

                    InlineKeyboardButton(
                        text="🔔 Notifikasi Code",
                        url="https://t.me/+T8c4gdEWf843ZWQ1"
                    )
                ]
            ]
        )


        nav_msg = await bot.send_message(
            chat_id,
            (
                f"📦 NAVIGATION\n"
                f"Page {page}/{total_page}"
            ),
            reply_markup=keyboard
        )


        NAV_CACHE[
            (user_id, code)
        ] = nav_msg.message_id



        print(
            "SEND PAGE SUCCESS",
            code,
            page,
            sent
        )


        return True



    except Exception as e:

        print(
            "SEND PAGE ERROR",
            repr(e)
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
