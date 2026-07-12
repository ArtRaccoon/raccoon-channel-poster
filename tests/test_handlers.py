import sys

from aiogram import Router

from bot.handlers import BatchNotifier, create_router


class DummyDB:
    pass


class DummyBot:
    pass


def test_create_router_does_not_import_main():
    sys.modules.pop("bot.main", None)

    router = create_router(
        db=DummyDB(),
        bot=DummyBot(),
        interval_hours=3,
        timezone_name="Europe/Moscow",
        notifier=BatchNotifier(DummyDB(), enabled=False, delay=0),
        admin_ids={1},
    )

    assert isinstance(router, Router)
    assert "bot.main" not in sys.modules
