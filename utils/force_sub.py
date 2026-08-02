import logging

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
)

# =========================
# FORCE SUB CHANNELS
# =========================
CHANNELS = [
    -1003978483597,
    -1004413314849,
]


# =========================
# CHECK FORCE SUB
# =========================
async def check_force_sub(bot: Bot, user_id: int) -> bool:
    """
    Return:
        True  -> User sudah join semua channel.
        False -> User belum join / terjadi error.
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

        except TelegramBadRequest:
            logging.exception(
                "ForceSub TelegramBadRequest | %s",
                channel_id
            )
            return False

        except TelegramForbiddenError:
            logging.exception(
                "ForceSub TelegramForbiddenError | %s",
                channel_id
            )
            return False

        except Exception:
            logging.exception(
                "ForceSub Unknown Error | %s",
                channel_id
            )
            return False

    return True
