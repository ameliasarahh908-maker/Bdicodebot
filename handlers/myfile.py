from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from database import get_pool


router = Router()


@router.callback_query(F.data.startswith("myfile:"))
async def myfile_detail(call: CallbackQuery):

    code = call.data.split(":", 1)[1]

    user_id = call.from_user.id


    pool = await get_pool()


    file = await pool.fetchrow(
        """
        SELECT
            f.title,
            f.code,
            f.price,
            f.is_paid,
            f.media_count,

            (
                SELECT COUNT(*)
                FROM file_purchases p
                WHERE p.file_code=f.code
                AND p.status='paid'
            ) AS sold,


            (
                SELECT COALESCE(
                    SUM(p.paid_price),
                    0
                )
                FROM file_purchases p
                WHERE p.file_code=f.code
                AND p.status='paid'
            ) AS income


        FROM files f

        WHERE f.code=$1
        AND f.owner_id=$2

        LIMIT 1
        """,
        code,
        user_id
    )


    if not file:

        return await call.answer(
            "❌ File tidak ditemukan.",
            show_alert=True
        )



    harga = (
        "🆓 Gratis"
        if not file["is_paid"]
        else
        f"Rp {file['price']:,}".replace(",",".")
    )



    text = (
        "📦 <b>DETAIL FILE</b>\n"
        "━━━━━━━━━━━━━━\n\n"

        f"📁 Nama : <b>{file['title']}</b>\n"
        f"🔑 Code : <code>{file['code']}</code>\n\n"

        f"💰 Harga : {harga}\n"
        f"📦 Media : {file['media_count']}\n"
        f"🛒 Terjual : {file['sold']}x\n"
        f"💵 Pendapatan : Rp {file['income']:,}\n"

        "\n━━━━━━━━━━━━━━"
    ).replace(",", ".")



    kb = InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="🗑 Hapus File",
                    callback_data=f"delete_file:{code}"
                )
            ],

            [
                InlineKeyboardButton(
                    text="⬅️ Kembali",
                    callback_data="my_code"
                )
            ]

        ]
    )



    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb
    )


    await call.answer()
