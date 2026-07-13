import hmac
import hashlib
import logging

from fastapi import APIRouter, Request

from bot import bot
from database import fetchrow, execute
from utils.redis_client import redis_client
from handlers.page import send_page
from config import BAYARGG_SECRET

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bayargg", tags=["BayarGG"])

SECRET_KEY = BAYARGG_WEBHOOK_SECRET.encode()
ADMIN_CHAT_ID = -1004437365690


def secure_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a or "", b or "")


@router.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Callback-Signature", "")

    expected = hmac.new(
        SECRET_KEY,
        body,
        hashlib.sha256
    ).hexdigest()

    if not secure_compare(signature, expected):
        return {"success": False, "message": "invalid signature"}

    try:
        data = await request.json()
    except Exception:
        return {"success": False, "message": "invalid json"}

    invoice_id = str(data.get("invoice_id", "")).strip()
    status = str(data.get("status", "")).lower().strip()

    if not invoice_id:
        return {"success": False, "message": "missing invoice"}

    logger.info("Webhook | invoice=%s | status=%s", invoice_id, status)

    if status != "paid":
        return {"success": True, "message": "ignored"}

    # =========================
    # 🔒 ANTI DOUBLE PROCESS
    # =========================
    redis_key = f"webhook:bayargg:{invoice_id}"

    try:
        locked = await redis_client.set(redis_key, "1", ex=86400, nx=True)
        if not locked:
            return {"success": True, "message": "already processed"}
    except Exception:
        logger.exception("Redis error")

    # =========================
    # 💎 VIP PAYMENT
    # =========================
    vip_tx = await fetchrow(
        """
        SELECT user_id, amount, code, status
        FROM payments
        WHERE invoice_id=$1 AND type='vip'
        """,
        invoice_id
    )

    if vip_tx:
        updated = await execute(
            """
            UPDATE payments
            SET status='paid', updated_at=NOW()
            WHERE invoice_id=$1 AND status!='paid'
            """,
            invoice_id
        )

        if updated == "UPDATE 0":
            return {"success": True, "message": "vip already"}

        vip_days = {
            "vip1": 1, "vip3": 3, "vip5": 5,
            "vip7": 7, "vip10": 10,
            "vip20": 20, "vip30": 30
        }

        days = vip_days.get(vip_tx["code"], 30)

        await execute(
            """
            UPDATE users
            SET vip=TRUE,
                vip_until =
                CASE
                    WHEN vip_until IS NULL OR vip_until < NOW()
                    THEN NOW() + ($2 || ' days')::interval
                    ELSE vip_until + ($2 || ' days')::interval
                END
            WHERE telegram_id=$1
            """,
            vip_tx["user_id"], days
        )

        await bot.send_message(
            vip_tx["user_id"],
            (
                "💎 <b><i>VIP ACTIVATED</i></b>\n\n"
                f"<b><i>Duration:</i></b> {days} days"
            ),
            parse_mode="HTML"
        )

        return {"success": True}

    # =========================
    # 📂 FILE PAYMENT
    # =========================
    file_tx = await fetchrow(
        """
        SELECT user_id, owner_id, paid_price, file_code, status,
               qr_message_id, qr_chat_id
        FROM file_purchases
        WHERE payment_id=$1
        """,
        invoice_id
    )

    if not file_tx:
        return {"success": False, "message": "not found"}

    if file_tx["status"] == "paid":
        return {"success": True, "message": "already"}

    updated = await execute(
        """
        UPDATE file_purchases
        SET status='paid', paid_at=NOW()
        WHERE payment_id=$1 AND status='pending'
        """,
        invoice_id
    )

    if updated == "UPDATE 0":
        return {"success": True, "message": "already"}

    # =========================
    # ❌ HAPUS QR
    # =========================
    try:
        if file_tx["qr_message_id"]:
            await bot.delete_message(
                chat_id=file_tx["qr_chat_id"],
                message_id=file_tx["qr_message_id"]
            )
    except Exception:
        logger.exception("delete QR gagal")

    # =========================
    # 🔓 AKSES USER
    # =========================
    await execute(
        """
        INSERT INTO user_access (user_id, file_code)
        VALUES ($1, $2)
        ON CONFLICT DO NOTHING
        """,
        file_tx["user_id"],
        file_tx["file_code"]
    )

    # =========================
    # 📩 USER NOTIF
    # =========================
    await bot.send_message(
        file_tx["user_id"],
        (
            "✅ <b><i>PAYMENT SUCCESSFUL</i></b>\n\n"
            "<b><i>Your file is being delivered...</i></b>"
        ),
        parse_mode="HTML"
    )

    # =========================
    # 🚀 SEND FILE
    # =========================
    try:
        sent = await send_page(
            bot=bot,
            chat_id=file_tx["user_id"],
            user_id=file_tx["user_id"],
            code=file_tx["file_code"],
            page=1
        )

        if not sent:
            raise Exception("send gagal")

    except Exception:
        logger.exception("Gagal kirim file")

        await bot.send_message(
            file_tx["user_id"],
            (
                "⚠️ <b><i>DELIVERY FAILED</i></b>\n\n"
                "<b><i>Your payment was successful, but the file could not be sent automatically.</i></b>\n"
                "<b><i>Please contact admin.</i></b>"
            ),
            parse_mode="HTML"
        )

    # =========================
    # 💸 OWNER NOTIF
    # =========================
    try:
        await bot.send_message(
            file_tx["owner_id"],
            (
                "💰 <b><i>FILE SOLD</i></b>\n\n"
                f"<b><i>Code:</i></b> <code>{file_tx['file_code']}</code>\n"
                f"<b><i>Amount:</i></b> Rp {file_tx['paid_price']:,}"
            ).replace(",", "."),
            parse_mode="HTML"
        )
    except Exception:
        pass

    # =========================
    # 📊 ADMIN LOG
    # =========================
    try:
        await bot.send_message(
            ADMIN_CHAT_ID,
            (
                "💰 <b><i>PAYMENT RECEIVED</i></b>\n\n"
                f"<b><i>Invoice:</i></b> <code>{invoice_id}</code>\n"
                f"<b><i>User:</i></b> <code>{file_tx['user_id']}</code>\n"
                f"<b><i>File:</i></b> <code>{file_tx['file_code']}</code>\n"
                f"<b><i>Amount:</i></b> Rp {file_tx['paid_price']:,}"
            ).replace(",", "."),
            parse_mode="HTML"
        )
    except Exception:
        logger.exception("admin notify error")

    logger.info("SUCCESS invoice=%s", invoice_id)

    return {"success": True}
