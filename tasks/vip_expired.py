import asyncio
import logging

from database import execute

logger = logging.getLogger(__name__)


async def vip_expired_worker():

    while True:

        try:

            result = await execute(
                """
                UPDATE users
                SET
                    vip = FALSE
                WHERE vip = TRUE
                AND vip_until IS NOT NULL
                AND vip_until < NOW()
                """
            )

            if result != "UPDATE 0":
                logger.info(
                    "VIP expired cleaned: %s",
                    result
                )

        except Exception:
            logger.exception(
                "VIP expired worker error"
            )

        await asyncio.sleep(3600)
