import json
import logging
import httpx

from config import BAYARGG_API_KEY

logger = logging.getLogger(__name__)

BASE_URL = "https://www.bayar.gg/api"


class BayarGG:

    @staticmethod
    async def create_payment(
        amount: int,
        description: str,
        payment_url: str = "https://www.bayar.gg/pay",
        callback_url: str | None = None,
        redirect_url: str | None = None,
        customer_name: str | None = None,
        customer_phone: str | None = None,
        payment_method: str = "qris",
    ):

        headers = {
            "X-API-Key": BAYARGG_API_KEY,
            "Content-Type": "application/json"
        }

        payload = {
            "amount": amount,
            "description": description,
            "payment_url": payment_url,
            "payment_method": payment_method,
        }

        if callback_url:
            payload["callback_url"] = callback_url

        if redirect_url:
            payload["redirect_url"] = redirect_url

        if customer_name:
            payload["customer_name"] = customer_name

        if customer_phone:
            payload["customer_phone"] = customer_phone

        try:
            logger.info("🚀 CREATE PAYMENT")
            logger.info(json.dumps(payload, indent=2, ensure_ascii=False))

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{BASE_URL}/create-payment.php",
                    headers=headers,
                    json=payload
                )

            logger.info(f"STATUS: {response.status_code}")
            logger.info(f"BODY: {response.text}")

            response.raise_for_status()

            raw = response.json()

            if not raw.get("success"):
                raise Exception(
                    raw.get("error")
                    or raw.get("message")
                    or str(raw)
                )

            data = raw.get("data", raw)

            # =========================
            # NORMALISASI DATA (PENTING)
            # =========================
            invoice_id = (
                data.get("invoice_id")
                or data.get("id")
                or data.get("invoice")
            )

            qr_string = (
                data.get("qris_string")
                or data.get("qris")
                or data.get("qr_string")
                or data.get("qr")
            )

            final_amount = (
                data.get("final_amount")
                or data.get("amount")
                or amount
            )

            if not invoice_id:
                raise Exception("Invoice ID tidak ditemukan")

            if not qr_string:
                raise Exception("QR string tidak ditemukan")

            return {
                "invoice_id": invoice_id,
                "qris_string": qr_string,
                "final_amount": final_amount
            }

        except Exception as e:
            logger.exception(f"❌ CREATE PAYMENT ERROR: {e}")
            return None

    @staticmethod
    async def check_payment(invoice_id: str):

        headers = {
            "X-API-Key": BAYARGG_API_KEY
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{BASE_URL}/check-payment.php",
                    headers=headers,
                    params={"invoice": invoice_id}
                )

            logger.info(f"CHECK STATUS: {response.status_code}")
            logger.info(f"CHECK BODY: {response.text}")

            response.raise_for_status()

            raw = response.json()

            if not raw.get("success"):
                raise Exception(
                    raw.get("error")
                    or raw.get("message")
                    or str(raw)
                )

            data = raw.get("data", raw)

            status = str(
                data.get("status")
                or data.get("payment_status")
                or ""
            ).lower()

            return {
                "invoice_id": invoice_id,
                "status": status,
                "raw": data
            }

        except Exception as e:
            logger.exception(f"❌ CHECK PAYMENT ERROR: {e}")
            return None
