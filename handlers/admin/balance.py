from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import get_pool
from .dashboard import is_admin, rupiah


router = Router()


# =========================
# STATE
# =========================

class BalanceAdminState(StatesGroup):
    waiting_user = State()



# =========================
# MENU BALANCE
# =========================

@router.callback_query(F.data == "admin_balance")
async def admin_balance(
    call: CallbackQuery,
    state: FSMContext
):

    if not is_admin(call.from_user.id):
        return await call.answer(
            "❌ Tidak memiliki akses",
            show_alert=True
        )


    await state.clear()

    await state.set_state(
        BalanceAdminState.waiting_user
    )


    kb = InlineKeyboardBuilder()

    kb.button(
        text="⬅ Kembali",
        callback_data="admin_home"
    )


    await call.message.edit_text(
        (
            "💰 <b>USER FINANCE</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "Kirim:\n"
            "• Telegram ID\n"
            "• Username (@username)"
        ),
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )


    await call.answer()



# =========================
# PROCESS USER
# =========================

@router.message(BalanceAdminState.waiting_user)
async def process_balance(
    message: Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        await state.clear()
        return


    key = (
        message.text or ""
    ).strip()


    if not key:
        return await message.answer(
            "❌ Input kosong."
        )


    pool = await get_pool()


    # =====================
    # SEARCH ID
    # =====================

    if key.isdigit():

        user = await pool.fetchrow(
            """
            SELECT
                chat_id,
                username,
                full_name,

                balance,

                total_earn,
                total_deposit,
                total_withdraw,

                total_upload,
                total_download,
                total_file,

                plan,

                vip,
                vip_until,

                vvip,
                vvip_until,

                is_banned

            FROM users

            WHERE chat_id=$1
            """,
            int(key)
        )


    # =====================
    # SEARCH USERNAME
    # =====================

    else:

        username = (
            key
            .replace("@","")
            .lower()
        )


        user = await pool.fetchrow(
            """
            SELECT
                chat_id,
                username,
                full_name,

                balance,

                total_earn,
                total_deposit,
                total_withdraw,

                total_upload,
                total_download,
                total_file,

                plan,

                vip,
                vip_until,

                vvip,
                vvip_until,

                is_banned

            FROM users

            WHERE LOWER(username)=$1
            """,
            username
        )



    if not user:

        await state.clear()

        return await message.answer(
            "❌ User tidak ditemukan."
        )



    # =====================
    # MEMBERSHIP
    # =====================

    if user["vvip"]:

        member = (
            f"👑 VVIP\n"
            f"📅 Sampai : {user['vvip_until']}"
        )

    elif user["vip"]:

        member = (
            f"🔥 VIP\n"
            f"📅 Sampai : {user['vip_until']}"
        )

    else:

        member = "🆓 FREE"



    banned = (
        "🚫 BANNED"
        if user["is_banned"]
        else
        "✅ ACTIVE"
    )



    text = (

        "👤 <b>USER FINANCE DETAIL</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"

        f"🆔 ID : <code>{user['chat_id']}</code>\n"
        f"👤 Username : @{user['username'] or '-'}\n"
        f"📛 Nama : {user['full_name'] or '-'}\n\n"


        "💎 <b>MEMBERSHIP</b>\n"
        f"{member}\n\n"


        "💰 <b>KEUANGAN</b>\n"
        f"👛 Balance : {rupiah(user['balance'])}\n"
        f"💵 Total Earn : {rupiah(user['total_earn'])}\n"
        f"📥 Deposit : {rupiah(user['total_deposit'])}\n"
        f"📤 Withdraw : {rupiah(user['total_withdraw'])}\n\n"


        "📂 <b>FILE STATISTIC</b>\n"
        f"📤 Upload : {user['total_upload']}\n"
        f"📥 Download : {user['total_download']}\n"
        f"📁 Total File : {user['total_file']}\n\n"


        "🔐 <b>STATUS</b>\n"
        f"{banned}"

    )


    kb = InlineKeyboardBuilder()

    kb.button(
        text="⬅ Admin Menu",
        callback_data="admin_home"
    )


    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )


    await state.clear()
