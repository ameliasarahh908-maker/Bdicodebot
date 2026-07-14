import asyncio
import logging

from database import fetch, execute
from bot import bot
from handlers.page import send_page


async def payment_worker():

    logging.info("💳 Payment worker running...")

    while True:

        try:

            # cari payment pending yang belum diproses
            payments = await fetch(
                """
                SELECT
                    id,
                    user_id,
                    code,
                    invoice_id
                FROM payments
                WHERE status='paid'
                  AND type='file'
                LIMIT 20
                """
            )


            for p in payments:

                try:

                    # kirim file otomatis
                    sent = await send_page(
                        bot=bot,
                        chat_id=p["user_id"],
                        user_id=p["user_id"],
                        code=p["code"],
                        page=1
                    )


                    if sent:

                        await execute(
                            """
                            UPDATE payments
                            SET
                                status='completed',
                                updated_at=NOW()
                            WHERE id=$1
                            """,
                            p["id"]
                        )


                        logging.info(
                            "✅ File sent %s",
                            p["invoice_id"]
                        )


                except Exception:

                    logging.exception(
                        "❌ Failed send file %s",
                        p["invoice_id"]
                    )


        except Exception:

            logging.exception(
                "💥 PAYMENT WORKER ERROR"
            )


        await asyncio.sleep(15)
