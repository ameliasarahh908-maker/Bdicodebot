import logging

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
)

# =========================
# FORCE SUB CHANNELS (FIX)
# =========================
CHANNELS = [
    -1004419102427,  # channel utama
    -1004437365690,  # group chat
]


# =========================
# CHECK FORCE SUB
# =========================
async def check_force_sub(bot: Bot, user_id: int) -> bool:
    """
    Return:
        True  -> User sudah join semua channel.
        False -> User belum join salah satu channel.
    """

    for channel_id in CHANNELS:
        try:
            member = await bot.get_chat_member(
                chat_id=channel_id,
                user_id=user_id,
            )

            if member.status not in (
                "member",
                "administrator",
                "creator",
            ):
                return False

        except TelegramBadRequest as e:
            logging.error(
                "ForceSub TelegramBadRequest | Channel=%s User=%s Error=%s",
                channel_id,
                user_id,
                e,
            )
            return True  # biar bot gak ngeblok user kalau error

        except TelegramForbiddenError as e:
            logging.error(
                "ForceSub TelegramForbiddenError | Channel=%s User=%s Error=%s",
                channel_id,
                user_id,
                e,
            )
            return True

        except Exception:
            logging.exception(
                "ForceSub Unknown Error | Channel=%s User=%s",
                channel_id,
                user_id,
            )
            return True

    return True
