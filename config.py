import os
from dotenv import load_dotenv

load_dotenv()

# =========================
# GENERAL
# =========================
TIMEZONE = "Asia/Jakarta"

# =========================
# BOT
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = "ZyxFidxBot"

# =========================
# DATABASE
# =========================
DATABASE_URL = os.getenv("DATABASE_URL")

# =========================
# PAYMENT (BayarGG)
# =========================
BAYARGG_API_KEY = os.getenv("BAYARGG_API_KEY")
BAYARGG_MERCHANT = os.getenv("BAYARGG_MERCHANT")
BAYARGG_WEBHOOK_SECRET = os.getenv("BAYARGG_WEBHOOK_SECRET")

# =========================
# CHANNEL & GROUP
# =========================
CHANNEL_ID = -1004395938795
GROUP_ID = -1004437365690

# =========================
# ADMIN
# =========================
ADMIN_IDS = [
    int(x)
    for x in os.getenv("ADMIN_IDS", "6847035364").split(",")
    if x.strip().isdigit()
]

# =========================
# VALIDATION
# =========================
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN belum di-set di .env")

if not BAYARGG_API_KEY:
    raise ValueError("BAYARGG_API_KEY belum di-set")

if not BAYARGG_WEBHOOK_SECRET:
    raise ValueError("BAYARGG_WEBHOOK_SECRET belum di-set")
