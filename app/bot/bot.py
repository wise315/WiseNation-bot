from aiogram import Bot, Dispatcher

from app.bot.handlers.collection import router as collection_router
from app.bot.handlers.menu import router as menu_router
from app.bot.handlers.start import router as start_router
from app.bot.handlers.wallet import router as wallet_router


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()

    dispatcher.include_router(start_router)
    dispatcher.include_router(menu_router)
    dispatcher.include_router(wallet_router)
    dispatcher.include_router(collection_router)

    return dispatcher


def create_bot(token: str) -> Bot:
    return Bot(token=token)