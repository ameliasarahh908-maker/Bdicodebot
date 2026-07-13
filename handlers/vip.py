from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

router = Router()


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


@router.callback_query(F.data == "vip_plan")
async def vip_plan(call):

    await call.answer()

    await call.message.answer(
        "<b><i>💎 VIP PLAN</i></b>\n\n"
        "<b><i>🚧 This feature is still under development.</i></b>",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "vvip_plan")
async def vvip_plan(call):

    await call.answer()

    await call.message.answer(
        "<b><i>👑 VVIP PLAN</i></b>\n\n"
        "<b><i>🚧 This feature is still under development.</i></b>",
        parse_mode="HTML"
    )
