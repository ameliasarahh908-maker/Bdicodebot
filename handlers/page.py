import time
import json

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import get_pool

from services.page_service import send_page
from services.access_service import check_access

from utils.cache import (
    PAGE_CACHE,
    PAGE_CHANGE,
    USER_LOCK,
    NAV_CACHE
)

router = Router()

SAME_PAGE_COOLDOWN = 3600      # 1 jam
CHANGE_PAGE_COOLDOWN = 15      # 15 detik


# =========================
# PAGE HANDLER
# =========================
@router.callback_query(F.data.startswith("page:"))
async def page_handler(call: CallbackQuery):

    user_id = call.from_user.id

    try:
        _, code, page = call.data.split(":")
        page = int(page)
    except:
        return await call.answer("❌ Invalid data", show_alert=True)

    now = time.time()
    key = (user_id, code)

    # =========================
    # SAME PAGE COOLDOWN
    # =========================
    last = PAGE_CACHE.get(key)

    if last:
        last_page, last_time = last

        if last_page == page:
            sisa = SAME_PAGE_COOLDOWN - (now - last_time)

            if sisa > 0:
                return await call.answer(
                    f"⏳ this page has been opened.\ntry again {int(sisa)} second.",
                    show_alert=True
                )

    # =========================
    # CHANGE PAGE COOLDOWN
    # =========================
    change = PAGE_CHANGE.get(key)

    if change:
        old_page, old_time = change

        if old_page != page:
            sisa = CHANGE_PAGE_COOLDOWN - (now - old_time)

            if sisa > 0:
                return await call.answer(
                    f"⏳ Loading.. {int(sisa)} detik",
                    show_alert=True
                )

    # update cache
    PAGE_CACHE[key] = (page, now)
    PAGE_CHANGE[key] = (page, now)

    async with USER_LOCK[user_id]:

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
            return await call.answer("❌ File Not Found", show_alert=True)

        # =========================
        # VALIDASI PAGE LIMIT
        # =========================
        media = file["media"]

        if isinstance(media, str):
            media = json.loads(media)

        total_page = max(1, (len(media) + 9) // 10)

        if page > total_page:
            return await call.answer("📄 Page is up.", show_alert=True)

        # =========================
        # ACCESS CHECK
        # =========================
        bought = await check_access(pool, user_id, file)

        if not bought:

            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=f"💳 Pay Rp {file['price']:,}".replace(",", "."),
                            callback_data=f"pay:{code}"
                        )
                    ]
                ]
            )

            await call.message.answer(
                "🔒 <b>PAID FILES</b>\n\n"
                f"💰 Price : Rp {file['price']:,}\n\n"
                "continue paying or upgrade your account to vip or vvip.",
                parse_mode="HTML",
                reply_markup=kb
            )

            return await call.answer()

        # =========================
        # DELETE NAV LAMA
        # =========================
        old_nav = NAV_CACHE.get((user_id, code))

        if old_nav:
            try:
                await call.bot.delete_message(
                    call.message.chat.id,
                    old_nav
                )
            except:
                pass

            NAV_CACHE.pop((user_id, code), None)

        # =========================
        # SEND PAGE
        # =========================
        await send_page(
            call.bot,
            call.message.chat.id,
            user_id,
            code,
            page
        )

        await call.answer()


# =========================
# END PAGE HANDLER
# =========================
@router.callback_query(F.data == "end_page")
async def end_page(call: CallbackQuery):

    await call.answer(
        "📄 all pages have been opened.",
        show_alert=True
    )
