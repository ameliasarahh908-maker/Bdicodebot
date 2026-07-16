import json,time

from aiogram import Router,F
from aiogram.types import Message,InlineKeyboardMarkup,InlineKeyboardButton

from utils.user import get_user_status
from database import get_pool

router=Router()


def safe_json(data):
    if isinstance(data,str):
        try:
            return json.loads(data)
        except:
            return []
    return data or []


def get_first_media(media):
    return media[0] if isinstance(media,list) and media else None


async def open_file_by_code(message:Message,code:str):

    pool=await get_pool()

    file=await pool.fetchrow(
        """
        SELECT *
        FROM files
        WHERE LOWER(code)=LOWER($1)
        LIMIT 1
        """,
        code
    )

    if not file:
        return await message.answer(
            "❌ File tidak ditemukan."
        )

    media=safe_json(file["media"])

    user_level=await get_user_status(
        pool,
        message.from_user.id
    )

    if not media:
        return await message.answer(
            "❌ File kosong."
        )

    expires_at=file["expires_at"]

    if expires_at:

        if hasattr(expires_at,"timestamp"):
            expired=expires_at.timestamp()<time.time()
        else:
            expired=expires_at<int(time.time())

        if expired:
            return await message.answer(
                "❌ File sudah kadaluarsa."
            )

    is_paid=file["is_paid"] or False
    price=file["price"] or 0

    owner=(
        message.from_user.id==
        file["owner_id"]
    )

    access=await pool.fetchval(
        """
        SELECT EXISTS(
            SELECT 1
            FROM file_purchases
            WHERE user_id=$1
            AND file_code=$2
            AND status='paid'
        )
        """,
        message.from_user.id,
        code
    )

    has_access=(
        owner
        or access
        or user_level=="vip"
        or user_level=="vvip"
    )


    if is_paid and not has_access:

        keyboard=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"💳 BAYAR Rp {price:,}".replace(",","."),
                        callback_data=f"pay:{code}"
                    )
                ]
            ]
        )

        return await message.answer(
            (
                "🔒 <b>FILE BERBAYAR</b>\n\n"
                f"🔑 CODE : <code>{code}</code>\n"
                f"💰 HARGA : Rp {price:,}\n\n"
                "Silakan bayar untuk membuka file."
            ).replace(",","."),
            parse_mode="HTML",
            reply_markup=keyboard
        )


    from handlers.open_menu import open_keyboard

    return await message.answer(
        (
            "✅ <b>FILE DITEMUKAN</b>\n\n"
            f"📦 Total Media : <b>{len(media)}</b>\n\n"
            "Pilih metode pengiriman:"
        ),
        parse_mode="HTML",
        reply_markup=open_keyboard(code)
    )


import re

@router.message(F.text)
async def auto_get_file(message:Message):

    if not message.text:
        return

    text=message.text

    match=re.search(
        r"Zyx\d{8}File\d{8}",
        text,
        re.IGNORECASE
    )
    if not match:
        return

    code=match.group(0)
    
    await open_file_by_code(
        message,
        code
    )
