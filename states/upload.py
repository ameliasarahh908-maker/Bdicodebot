from aiogram.fsm.state import State, StatesGroup

class UploadState(StatesGroup):
    waiting_media = State()
    confirm_done = State()
    choose_access = State()
    set_price = State()
    set_title = State()
