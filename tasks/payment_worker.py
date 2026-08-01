import asyncio
import logging

from database import fetch, fetchrow, execute
from bot import bot
from handlers.page import send_page


async def payment_worker():

    logging.info("💳 Payment worker running...")

    while True:

        try:

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

                    file = await fetchrow(
                        """
                        SELECT
                            owner_id,
                            price
                        FROM files
                        WHERE LOWER(TRIM(code)) =
                              LOWER(TRIM($1))
                        LIMIT 1
                        """,
                        p["code"]
                    )


                    if not file:

                        logging.warning(
                            "File tidak ditemukan %s",
                            p["code"]
                        )

                        continue



                    # =========================
                    # KIRIM FILE KE PEMBELI
                    # =========================

                    sent = await send_page(
                        bot=bot,
                        chat_id=p["user_id"],
                        user_id=p["user_id"],
                        code=p["code"],
                        page=1
                    )


                    if sent:


                        # =========================
                        # KOMISI SELLER 50%
                        # =========================

                        seller_earn = int(
                            file["price"] * 0.5
                        )


                        if seller_earn > 0:

                            await execute(
                                """
                                UPDATE users
                                SET
                                    balance = balance + $1,
                                    total_earn = total_earn + $1
                                WHERE user_id=$2
                                """,
                                seller_earn,
                                file["owner_id"]
                            )


                            logging.info(
                                "💰 Seller +%s user=%s",
                                seller_earn,
                                file["owner_id"]
                            )



                        # =========================
                        # SELESAIKAN PAYMENT
                        # =========================

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
