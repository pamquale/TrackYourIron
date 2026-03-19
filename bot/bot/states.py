from aiogram.fsm.state import State, StatesGroup


class TrackerState(StatesGroup):
    waiting_for_url = State()
    waiting_for_mode = State()
    waiting_for_price = State()
