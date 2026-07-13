from aiogram.fsm.state import StatesGroup, State


class GetFileState(StatesGroup):
    # State untuk menunggu user kirim code
    wait_code = State()
