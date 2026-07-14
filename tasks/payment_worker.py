import asyncio
import logging
from datetime import datetime

import aiohttp

from database import fetch, execute
from bot import bot


API_KEY = "API-91975f8ac089c185f5bb246e8a24fa9b0ddc2ff31c655e2e"


# =========================
# CEK BAYARGG API
# =========================
async def check_bayargg(order_id: str):
    url = f"https://api.bayargg.com/v1/transaction/{order_id}"

    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as res:
                data = await res.json()

                logging.info(f"🔍 BayarGG [{order_id}]: {data}")

                status = data.get("status")

                if status == "PAID":
                    return "paid"
                elif status in ["EXPIRED", "CANCELLED"]:
                    return "expired"

                return "pending"

    except Exception:
        logging.exception("❌ BayarGG API error")
        return "pending"


# =========================
# KIRIM FILE KE USER
# =========================
async def send_file(user_id: int, code: str):
    file_path = f"files/{code}.txt"

    try:
        with open(file_path, "rb") as f:
            await bot.send_document(
                user_id,
                f,
                caption="📦 File kamu sudah siap!\nTerima kasih sudah membeli 🙏"
            )
    except Exception:
        logging.exception("❌ Gagal kirim file")


# =========================
# PAYMENT WORKER
# =========================
async def payment_worker():
    logging.info("💳 Payment worker running...")

    while True:
        try:
            payments = await fetch("""
                SELECT id, order_id, user_id, code, amount, expires_at
                FROM payments
                WHERE status = 'pending'
                LIMIT 50
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

                    logging.info(f"⏰ Expired: {p['order_id']}")
                    continue

                # =========================
                # CEK BAYARGG
                # =========================
                status = await check_bayargg(p["order_id"])

                if status == "expired":
                    await execute("""
                        UPDATE payments
                        SET status = 'expired'
                        WHERE id = $1 AND status = 'pending'
                    """, payment_id)

                    logging.info(f"❌ Expired (API): {p['order_id']}")
                    continue

                if status == "paid":
                    result = await execute("""
                        UPDATE payments
                        SET status = 'paid'
                        WHERE id = $1 AND status = 'pending'
                    """, payment_id)

                    # anti double proses
                    if result == "UPDATE 0":
                        continue

                    # =========================
                    # SIMPAN PEMBELIAN
                    # =========================
                    await execute("""
                        INSERT INTO file_purchases (user_id, code)
                        VALUES ($1, $2)
                        ON CONFLICT DO NOTHING
                    """, p["user_id"], p["code"])

                    logging.info(f"✅ Paid: {p['order_id']}")

                    # =========================
                    # KIRIM FILE
                    # =========================
                    await send_file(p["user_id"], p["code"])

                # biar gak spam API
                await asyncio.sleep(1)

        except Exception:
            logging.exception("💥 PAYMENT WORKER ERROR")

        await asyncio.sleep(10)
