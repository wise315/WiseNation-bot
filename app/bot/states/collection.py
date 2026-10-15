from aiogram.fsm.state import State, StatesGroup


class CollectionStates(StatesGroup):
    waiting_for_contract_address = State()