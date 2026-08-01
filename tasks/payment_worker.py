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
                    invoice_id,
                    seller_paid
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
                    # KIRIM FILE PEMBELI
                    # =========================

                    sent = await send_page(
                        bot=bot,
                        chat_id=p["user_id"],
                        user_id=p["user_id"],
                        code=p["code"],
                        page=1
                    )


                    if not sent:
                        continue



                    # =========================
                    # KOMISI SELLER 50%
                    # =========================

                    if not p["seller_paid"]:

                        seller_id = file["owner_id"]
                        price = file["price"] or 0

                        seller_earn = int(
                            price * 0.5
                        )


                        if seller_id and seller_earn > 0:


                            await execute(
                                """
                                UPDATE users
                                SET
                                    balance = balance + $1,
                                    total_earn = total_earn + $1
                                WHERE user_id=$2
                                """,
                                seller_earn,
                                seller_id
                            )


                            logging.info(
                                "💰 Seller mendapat Rp%s user=%s",
                                seller_earn,
                                seller_id
                            )



                        await execute(
                            """
                            UPDATE payments
                            SET
                                seller_paid=true
                            WHERE id=$1
                            """,
                            p["id"]
                        )



                    # =========================
                    # PAYMENT SELESAI
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
                        "❌ Failed payment %s",
                        p["invoice_id"]
                    )



        except Exception:

            logging.exception(
                "💥 PAYMENT WORKER ERROR"
            )



        await asyncio.sleep(15)
