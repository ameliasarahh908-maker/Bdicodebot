import hmac
import hashlib
import logging
import asyncio

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request

from bot import bot
from config import BAYARGG_WEBHOOK_SECRET
from config_vip import VIP_PACKAGES
from database import get_pool
from utils.redis_client import redis_client
from handlers.page import send_page

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bayargg", tags=["BayarGG"])


def secure_compare(a: str, b: str):
    return hmac.compare_digest(a or "", b or "")


@router.post("/webhook")
async def bayargg_webhook(request: Request):
    body = await request.body()

    signature = request.headers.get("X-Webhook-Signature", "")
    timestamp = request.headers.get("X-Webhook-Timestamp", "")

    try:
        data = await request.json()
    except Exception:
        logger.exception("INVALID JSON")
        return {"success": False}

    # ==========================
    # VERIFY SIGNATURE
    # ==========================
    signature_data = (
        f"{data['invoice_id']}|"
        f"{data['status']}|"
        f"{data['final_amount']}|"
        f"{timestamp}"
    )

    expected = hmac.new(
        BAYARGG_WEBHOOK_SECRET.encode(),
        signature_data.encode(),
        hashlib.sha256
    ).hexdigest()

    if not secure_compare(signature, expected):
        logger.warning("INVALID SIGNATURE")
        return {"success": False}

    invoice_id = data.get("invoice_id")
    status = (data.get("status") or "").lower()

    logger.info("WEBHOOK | %s | %s", invoice_id, status)

    if not invoice_id:
        return {"success": False}

    if status != "paid":
        return {"success": True}

    pool = await get_pool()

    # ==========================
    # LOCK (ANTI DOUBLE)
    # ==========================
    lock_key = f"payment_processing:{invoice_id}"

    if await redis_client.get(lock_key):
        return {"success": True}

    await redis_client.set(lock_key, "1", ex=300)

    try:

        # =================================
        # FILE PAYMENT
        # =================================
        purchase = await pool.fetchrow(
            "SELECT * FROM file_purchases WHERE payment_id=$1",
            invoice_id
        )

        if purchase:

            file = await pool.fetchrow(
                "SELECT * FROM files WHERE code=$1",
                purchase["file_code"]
            )

            if not file:
                logger.error("FILE NOT FOUND")
                return {"success": False}

            income = int(file["price"] * 0.9)

            # ==========================
            # UPDATE DB
            # ==========================
            if purchase["status"] != "paid":

                async with pool.acquire() as conn:
                    async with conn.transaction():

                        await conn.execute(
                            """
                            UPDATE file_purchases
                            SET status='paid', paid_at=NOW()
                            WHERE payment_id=$1
                            """,
                            invoice_id
                        )

                        await conn.execute(
                            """
                            UPDATE users
                            SET balance=balance+$1,
                                total_sales=total_sales+1,
                                total_income=total_income+$1
                            WHERE telegram_id=$2
                            """,
                            income,
                            file["owner_id"]
                        )

                logger.info("PAYMENT SUCCESS")

            # ==========================
            # DELETE QR
            # ==========================
            try:
                if purchase["qr_chat_id"] and purchase["qr_message_id"]:
                    await bot.delete_message(
                        chat_id=purchase["qr_chat_id"],
                        message_id=purchase["qr_message_id"]
                    )
            except Exception:
                logger.exception("DELETE QR ERROR")

            # ==========================
            # ✅ AUTO SEND FILE
            # ==========================
            success = False

            for _ in range(3):
                try:
                    await send_page(
                        bot=bot,
                        chat_id=purchase["user_id"],
                        user_id=purchase["user_id"],
                        code=purchase["file_code"],
                        page=1
                    )
                    success = True
                    break
                except Exception as e:
                    logger.error(f"Retry send error: {e}")
                    await asyncio.sleep(1)

            if success:
                await bot.send_message(
                    purchase["user_id"],
                    "✅ Pembayaran berhasil! File langsung dikirim."
                )
            else:
                await bot.send_message(
                    purchase["user_id"],
                    "⚠️ File gagal dikirim, hubungi admin."
                )

            return {"success": True}

        # =================================
        # VIP / VVIP PAYMENT
        # =================================

        trx = await pool.fetchrow(
            """
            SELECT *
            FROM payments
            WHERE invoice_id=$1
            """,
            invoice_id
        )


        if not trx:
            return {"success": False}



        paket = VIP_PACKAGES.get(
            trx["code"]
        )


        if not paket:
            return {"success": False}



        paket_type = paket.get(
            "type",
            "vip"
        )


        now = datetime.now(timezone.utc)



        user = await pool.fetchrow(
            """
            SELECT
                vip_until,
                vvip_expired
            FROM users
            WHERE id=$1
            """,
            trx["user_id"]
        )



        # =========================
        # HITUNG MASA AKTIF
        # =========================

        if paket_type == "vvip":

            if (
                user
                and user["vvip_expired"]
                and user["vvip_expired"] > now
            ):
                expired = (
                    user["vvip_expired"]
                    +
                    timedelta(
                        days=paket["days"]
                    )
                )

            else:

                expired = (
                    now
                    +
                    timedelta(
                        days=paket["days"]
                    )
                )


        else:

            if (
                user
                and user["vip_until"]
                and user["vip_until"] > now
            ):

                expired = (
                    user["vip_until"]
                    +
                    timedelta(
                        days=paket["days"]
                    )
                )

            else:

                expired = (
                    now
                    +
                    timedelta(
                        days=paket["days"]
                    )
                )



        async with pool.acquire() as conn:

            async with conn.transaction():


                # update pembayaran

                await conn.execute(
                    """
                    UPDATE payments
                    SET status='paid'
                    WHERE invoice_id=$1
                    """,
                    invoice_id
                )



                # =========================
                # VVIP
                # =========================

                if paket_type == "vvip":

                    await conn.execute(
                        """
                        UPDATE users
                        SET
                            is_vvip=TRUE,
                            vvip_expired=$1,
                            vip=TRUE,
                            vip_until=$1
                        WHERE id=$2
                        """,
                        expired,
                        trx["user_id"]
                    )


                # =========================
                # VIP
                # =========================

                else:

                    await conn.execute(
                        """
                        UPDATE users
                        SET
                            vip=TRUE,
                            vip_until=$1
                        WHERE id=$2
                        """,
                        expired,
                        trx["user_id"]
                    )



        if paket_type == "vvip":

            await bot.send_message(
                trx["user_id"],
                (
                    "💎 <b>VVIP AKTIF</b>\n\n"
                    "✅ Bisa upload file\n"
                    "✅ Akses premium\n"
                    f"⏳ Aktif sampai {expired:%d-%m-%Y %H:%M}"
                ),
                parse_mode="HTML"
            )


        else:

            await bot.send_message(
                trx["user_id"],
                (
                    "💠 <b>VIP AKTIF</b>\n\n"
                    "✅ Akses premium\n"
                    "❌ Upload belum tersedia\n"
                    f"⏳ Aktif sampai {expired:%d-%m-%Y %H:%M}"
                ),
                parse_mode="HTML"
            )



        return {"success": True}
