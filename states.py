from aiogram.fsm.state import State, StatesGroup


# =========================
# 📤 UPLOAD FLOW (AUTO)
# =========================
class UploadState(StatesGroup):
    waiting_media = State()
    confirm_done = State()
    choose_access = State()
    set_price = State()
    set_title = State()


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
