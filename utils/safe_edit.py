from aiogram.exceptions import TelegramBadRequest


async def safe_edit(
    message,
    text,
    reply_markup=None,
    parse_mode="HTML"
):
    try:
        await message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )

    except TelegramBadRequest as e:

        error = str(e)

        # Pesan sama, abaikan
        if "message is not modified" in error:
            return

        # Kalau gagal edit, kirim pesan baru
        try:
            await message.answer(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )

        except Exception:
            pass
