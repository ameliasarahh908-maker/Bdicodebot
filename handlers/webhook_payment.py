from fastapi import Request
import logging
import asyncio

from database import fetchrow, execute
from bot import bot
from handlers.page import send_page

logger = logging.getLogger(__name__)


async def bayar_webhook(request: Request):
    data = await request.json()

    logger.info(f"🔥 WEBHOOK MASUK: {data}")

    invoice_id = data.get("invoice_id")
    status = str(data.get("status", "")).lower()

    if not invoice_id:
        return {"ok": False}

    if status not in ["paid", "success"]:
        return {"ok": True}

    # =========================
    # AMBIL TRANSAKSI
    # =========================
    tx = await fetchrow(
        """
        SELECT user_id, file_code, status
        FROM file_purchases
        WHERE payment_id=$1
        """,
        invoice_id
    )

    if not tx:
        logger.warning(f"Invoice tidak ditemukan: {invoice_id}")
        return {"ok": True}

    if tx["status"] == "paid":
        logger.info(f"Sudah diproses: {invoice_id}")
        return {"ok": True}

    # =========================
    # UPDATE STATUS
    # =========================
    await execute(
        """
        UPDATE file_purchases
        SET status='paid', paid_at=NOW()
        WHERE payment_id=$1
        """,
        invoice_id
    )

    # =========================
    # KIRIM FILE (RETRY)
    # =========================
    for _ in range(3):
        try:
            await send_page(
                bot=bot,
                chat_id=tx["user_id"],
                user_id=tx["user_id"],
                code=tx["file_code"],
                page=1
            )

            await bot.send_message(
                tx["user_id"],
                "✅ Pembayaran berhasil! File sudah dikirim."
            )

            logger.info(f"✅ FILE TERKIRIM: {invoice_id}")
            break

        except Exception as e:
            logger.error(f"Retry send gagal: {e}")
            await asyncio.sleep(1)

    return {"ok": True}
