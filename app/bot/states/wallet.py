from aiogram.fsm.state import State, StatesGroup


class AddWalletStates(StatesGroup):
    waiting_for_address = State()
    waiting_for_label = State()