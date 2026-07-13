import hmac
import hashlib
import logging

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from bot import bot
from config import (
    BAYARGG_WEBHOOK_SECRET,
    CHANNEL_ID
)
from config_vip import VIP_PACKAGES
from database import get_pool
from utils.redis_client import redis_client
from handlers.page import send_page


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/bayargg",
    tags=["BayarGG"]
)


def secure_compare(a: str, b: str):
    return hmac.compare_digest(
        a or "",
        b or ""
    )



@router.post("/webhook")
async def bayargg_webhook(request: Request):

    body = await request.body()

    signature = request.headers.get("X-Webhook-Signature", "")
    timestamp = request.headers.get("X-Webhook-Timestamp", "")

    # ==========================
    # ✅ TIMESTAMP VALIDATION
    # ==========================
    try:
        ts = int(timestamp)
        now_ts = int(datetime.now(timezone.utc).timestamp())

        if abs(now_ts - ts) > 300:
            logger.warning("EXPIRED WEBHOOK")
            return {"success": False}

        logger.info("TIMESTAMP OK")

    except Exception:
        logger.warning("INVALID TIMESTAMP")
        return {"success": False}

    # ==========================
    # PARSE JSON
    # ==========================
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

    logger.info("SIGNATURE OK")

    invoice_id = data.get("invoice_id")
    status = (data.get("status") or "").lower()

    logger.info("WEBHOOK RECEIVED | %s | %s", invoice_id, status)

    if not invoice_id:
        return {"success": False}

    if status != "paid":
        return {"success": True}

    pool = await get_pool()

    # ==========================
    # 🔒 REDIS LOCK
    # ==========================
    lock_key = f"payment_processing:{invoice_id}"

    locked = await redis_client.set(lock_key, "1", ex=300, nx=True)
    if not locked:
        logger.info("PAYMENT LOCKED %s", invoice_id)
        return {"success": True}

    try:

        # =================================
        # FILE PAYMENT
        # =================================
        purchase = await pool.fetchrow(
            "SELECT * FROM file_purchases WHERE payment_id=$1",
            invoice_id
        )

        if purchase:

            if purchase["status"] == "paid":
                logger.info("SKIP DUPLICATE PAYMENT")
                return {"success": True}

            file = await pool.fetchrow(
                "SELECT * FROM files WHERE code=$1",
                purchase["file_code"]
            )

            if not file:
                logger.error("FILE NOT FOUND")
                return {"success": False}

            price = int(file["price"] or 0)
            income = int(price * 0.9)

            async with pool.acquire() as conn:
                async with conn.transaction():

                    result = await conn.execute(
                        """
                        UPDATE file_purchases 
                        SET status='paid', paid_at=NOW() 
                        WHERE payment_id=$1 AND status!='paid'
                        """,
                        invoice_id
                    )

                    if result == "UPDATE 0":
                        logger.info("ALREADY PROCESSED (DB LEVEL)")
                        return {"success": True}

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

            logger.info("FILE PAYMENT SUCCESS")

            # ==========================
            # NOTIFICATIONS
            # ==========================

            try:
                await bot.send_message(
                    file["owner_id"],
                    (
                        "💰 <b>FILE SOLD</b>\n\n"
                        f"📂 Code: <code>{purchase['file_code']}</code>\n"
                        f"💵 Earnings: <b>Rp {income:,}</b>"
                    ).replace(",", "."),
                    parse_mode="HTML"
                )
            except Exception:
                logger.exception("OWNER NOTIF FAILED")

            try:
                await bot.send_message(
                    -1004437365690,
                    (
                        "✅ <b>FILE SOLD</b>\n\n"
                        f"📂 Code: <code>{purchase['file_code']}</code>\n"
                        f"👤 Buyer: <code>{purchase['user_id']}</code>\n"
                        f"💰 Price: <b>Rp {price:,}</b>"
                    ).replace(",", "."),
                    parse_mode="HTML"
                )
            except Exception:
                logger.exception("CHANNEL NOTIF FAILED")

            try:
                if purchase["qr_chat_id"] and purchase["qr_message_id"]:
                    await bot.delete_message(
                        purchase["qr_chat_id"],
                        purchase["qr_message_id"]
                    )
            except Exception:
                logger.exception("DELETE QR FAILED")

            try:
                kb = InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(
                            text="📂 Access File",
                            callback_data=f"page:{purchase['file_code']}:1"
                        )
                    ]]
                )

                await bot.send_message(
                    purchase["user_id"],
                    "🎉 <b>Payment Successful</b>\n\nTap button below to access file.",
                    parse_mode="HTML",
                    reply_markup=kb
                )
            except Exception:
                logger.exception("SEND ACCESS FAILED")

            return {"success": True}

        # =================================
        # VIP PAYMENT
        # =================================
        trx = await pool.fetchrow(
            "SELECT * FROM payments WHERE invoice_id=$1",
            invoice_id
        )

        if not trx:
            return {"success": False}

        if trx["status"] == "paid":
            logger.info("VIP ALREADY PROCESSED")
            return {"success": True}

        paket = VIP_PACKAGES.get(trx["code"])
        if not paket:
            return {"success": False}

        user = await pool.fetchrow(
            "SELECT vip_until FROM users WHERE telegram_id=$1",
            trx["user_id"]
        )

        now = datetime.now(timezone.utc)

        if user and user["vip_until"] and user["vip_until"] > now:
            vip_until = user["vip_until"] + timedelta(days=paket["days"])
        else:
            vip_until = now + timedelta(days=paket["days"])

        async with pool.acquire() as conn:
            async with conn.transaction():

                await conn.execute(
                    "UPDATE payments SET status='paid' WHERE invoice_id=$1",
                    invoice_id
                )

                await conn.execute(
                    """
                    UPDATE users
                    SET vip=TRUE,
                        vip_started_at=NOW(),
                        vip_until=$1
                    WHERE telegram_id=$2
                    """,
                    vip_until,
                    trx["user_id"]
                )

        await bot.send_message(
            trx["user_id"],
            f"🎉 <b>VIP ACTIVE</b>\nValid until: {vip_until:%d-%m-%Y}",
            parse_mode="HTML"
        )

        await bot.send_message(
            -1004437365690,
            f"💎 <b>NEW VIP</b>\nUser: <code>{trx['user_id']}</code>",
            parse_mode="HTML"
        )

        return {"success": True}

    finally:
        # ❌ BIARIN LOCK EXPIRE (JANGAN DIHAPUS)
        pass
