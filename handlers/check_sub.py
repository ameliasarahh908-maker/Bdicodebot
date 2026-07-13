import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery

from utils.force_sub import check_force_sub
from keyboards.join import join_kb
from handlers.start import render_home_fast
from database import get_pool

router = Router()


@router.callback_query(F.data == "check_sub")
async def check_sub_callback(call: CallbackQuery):

    user_id = call.from_user.id
    username = call.from_user.username or "unknown"

    logging.info(f"CHECK SUB CLICKED: {user_id}")

    try:
        ok = await check_force_sub(call.bot, user_id)

        if not ok:
            await call.answer(
                "❌ You haven't joined all channels.",
                show_alert=True
            )

            await call.message.edit_text(
                "❌ You haven't joined all channels.\n\n"
                "Please join first, then click CHECK again.",
                reply_markup=join_kb()
            )
            return

        pool = await get_pool()

        # =========================
        # AUTO CREATE USER
        # =========================
        await pool.execute(
            """
            INSERT INTO users (telegram_id, username)
            VALUES ($1, $2)
            ON CONFLICT (telegram_id) DO NOTHING
            """,
            user_id,
            username
        )

        # =========================
        # FETCH USER
        # =========================
        user = await pool.fetchrow(
            """
            SELECT username, vip, vip_until
            FROM users
            WHERE telegram_id=$1
            """,
            user_id
        )

        # =========================
        # FALLBACK
        # =========================
        if not user:
            logging.warning(f"USER NULL: {user_id}")

            await render_home_fast(
                call.bot,
                call.message,
                user_id,
                username,
                False  # vip
            )
            return

        await call.answer("✅ Verification successful")

        # =========================
        # HOME RENDER
        # =========================
        await render_home_fast(
            call.bot,
            call.message,
            user_id,
            user["username"] or username,
            user["vip"]  # kirim status vip
        )

    except Exception as e:
        logging.exception(f"CHECK SUB ERROR: {e}")
        await call.answer("❌ SYSTEM ERROR", show_alert=True)
