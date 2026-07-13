from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

router = Router()


# =========================
# VIP / VVIP MENU
# =========================
@router.message(F.text == "💎 VIP / VVIP")
async def vip_vvip(message: Message):

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💎 VIP",
                    callback_data="vip_plan"
                ),
                InlineKeyboardButton(
                    text="👑 VVIP",
                    callback_data="vvip_plan"
                )
            ]
        ]
    )

    await message.answer(
        "<b><i>💎 VIP / VVIP MEMBERSHIP</i></b>\n\n"
        "<i>Select your premium plan below.</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


# =========================
# VIP PLAN
# =========================
@router.callback_query(F.data == "vip_plan")
async def vip_plan(call: CallbackQuery):

    await call.answer("Opening VIP menu...")

    await call.message.answer(
        "<b><i>💎 VIP PLAN</i></b>\n\n"
        "<i>🚧 This feature is still under development.</i>",
        parse_mode="HTML"
    )


# =========================
# VVIP PLAN
# =========================
@router.callback_query(F.data == "vvip_plan")
async def vvip_plan(call: CallbackQuery):

    await call.answer("Opening VVIP menu...")

    await call.message.answer(
        "<b><i>👑 VVIP PLAN</i></b>\n\n"
        "<i>🚧 This feature is still under development.</i>",
        parse_mode="HTML"
    )
