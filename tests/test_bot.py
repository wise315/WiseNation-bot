from app.bot.bot import create_bot, create_dispatcher
from app.bot.handlers.menu import router as menu_router
from app.bot.handlers.start import router as start_router


def test_bot_can_be_created():
    bot = create_bot("123456:TEST_TOKEN")

    assert bot is not None


def test_dispatcher_has_bot_routers():
    dispatcher = create_dispatcher()

    assert start_router in dispatcher.sub_routers
    assert menu_router in dispatcher.sub_routers