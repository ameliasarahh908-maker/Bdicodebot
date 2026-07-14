import asyncio
import logging
from datetime import datetime

from database import fetch, execute


async def payment_worker():
    logging.info("💳 Payment worker running...")

    while True:
        try:
            # ambil semua payment pending
            payments = await fetch("""
                SELECT id, order_id, user_id, code, amount, expires_at
                FROM payments
                WHERE status = 'pending'
            """)

            now = datetime.utcnow()

            for p in payments:
                payment_id = p["id"]

                # =========================
                # CEK EXPIRED
                # =========================
                if p["expires_at"] and now > p["expires_at"]:
                    await execute("""
                        UPDATE payments
                        SET status = 'expired'
                        WHERE id = $1 AND status = 'pending'
                    """, payment_id)

                    logging.info(f"⏰ Payment expired: {p['order_id']}")
                    continue

                # =========================
                # TODO: CEK API BAYARGG
                # =========================
                # status = await check_bayargg(p["order_id"])

                status = None  # sementara dummy

                if status == "paid":
                    # =========================
                    # UPDATE STATUS (ANTI DOUBLE)
                    # =========================
                    result = await execute("""
                        UPDATE payments
                        SET status = 'paid'
                        WHERE id = $1 AND status = 'pending'
                    """, payment_id)

                    # kalau sudah pernah diproses, skip
                    if result == "UPDATE 0":
                        continue

                    # =========================
                    # SAVE PURCHASE
                    # =========================
                    await execute("""
                        INSERT INTO file_purchases (user_id, code)
                        VALUES ($1, $2)
                        ON CONFLICT DO NOTHING
                    """, p["user_id"], p["code"])

                    logging.info(f"✅ Payment success: {p['order_id']}")

                    # =========================
                    # TODO: KIRIM FILE KE USER
                    # =========================
                    # await send_file(p["user_id"], p["code"])

        except Exception:
            logging.exception("💥 PAYMENT WORKER ERROR")

        await asyncio.sleep(10)
