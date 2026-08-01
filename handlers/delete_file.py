from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from database import get_pool


router = Router()


# =====================================
# DELETE FILE
# =====================================

@router.callback_query(F.data.startswith("delete_file:"))
async def delete_file(call: CallbackQuery):

    code = call.data.split(":", 1)[1]

    user_id = call.from_user.id


    pool = await get_pool()


    # =========================
    # CEK FILE MILIK USER
    # =========================

    file = await pool.fetchrow(
        """
        SELECT
            code,
            title,
            owner_id
        FROM files
        WHERE code=$1
        LIMIT 1
        """,
        code
    )


    if not file:

        return await call.answer(
            "❌ File tidak ditemukan.",
            show_alert=True
        )


    if file["owner_id"] != user_id:

        return await call.answer(
            "❌ Kamu bukan pemilik file ini.",
            show_alert=True
        )



    # =========================
    # CEK SUDAH TERJUAL
    # =========================

    sold = await pool.fetchval(
        """
        SELECT COUNT(*)
        FROM file_purchases
        WHERE file_code=$1
        AND status='paid'
        """,
        code
    )


    if sold > 0:

        return await call.message.edit_text(
            (
                "🔒 <b>FILE TIDAK BISA DIHAPUS</b>\n\n"
                f"📁 File : <b>{file['title']}</b>\n"
                f"🛒 Sudah terjual : <b>{sold}x</b>\n\n"
                "File yang sudah dibeli user tidak bisa dihapus "
                "agar akses pembeli tetap aman."
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⬅️ Kembali",
                            callback_data=f"myfile:{code}"
                        )
                    ]
                ]
            )
        )



    # =========================
    # HAPUS MEDIA
    # =========================

    await pool.execute(
        """
        DELETE FROM medias
        WHERE code=$1
        """,
        code
    )


    # =========================
    # HAPUS FILE
    # =========================

    await pool.execute(
        """
        DELETE FROM files
        WHERE code=$1
        AND owner_id=$2
        """,
        code,
        user_id
    )



    await call.message.edit_text(
        (
            "✅ <b>FILE BERHASIL DIHAPUS</b>\n\n"
            f"📁 {file['title']}\n\n"
            "File sudah dihapus dari marketplace."
        ),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📦 My Code",
                        callback_data="my_code"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🏠 Home",
                        callback_data="home"
                    )
                ]
            ]
        )
    )


    await call.answer()
