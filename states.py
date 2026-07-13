from aiogram.fsm.state import State, StatesGroup


# =========================
# 📤 UPLOAD FLOW (AUTO)
# =========================
class UploadState(StatesGroup):
    input_price = State()
    uploading = State()


# =========================
# 🛒 BUY FLOW
# =========================
class BuyState(StatesGroup):
    waiting_payment = State()
    verifying = State()


# =========================
# 💳 PAYMENT
# =========================
class PaymentState(StatesGroup):
    waiting_callback = State()


# =========================
# 🛠 ADMIN
# =========================
class AdminState(StatesGroup):
    broadcast = State()
    user_action = State()
