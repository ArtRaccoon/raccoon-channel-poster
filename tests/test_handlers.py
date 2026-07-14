import sys

from aiogram import Router

from bot.handlers import BatchNotifier, create_router, main_menu_keyboard, clear_confirm_keyboard, parse_interval_value


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


def test_admin_menu_keyboards_contain_expected_buttons():
    menu = main_menu_keyboard()
    assert [[button.text for button in row] for row in menu.keyboard] == [
        ["📊 Статус", "📚 Очередь"],
        ["▶️ Опубликовать сейчас"],
        ["⏸ Пауза", "▶️ Продолжить"],
        ["⏱ Интервал", "🔗 Ссылки"],
        ["⚙️ Канал", "🔗 Настроить канал"],
        ["🗑 Очистить очередь"],
        ["❓ Помощь"],
    ]


def test_clear_confirm_keyboard_contains_confirmation_buttons():
    keyboard = clear_confirm_keyboard()
    assert [[button.text for button in row] for row in keyboard.keyboard] == [
        ["✅ Да, очистить очередь"],
        ["❌ Отмена"],
    ]


def test_setinterval_parsing_supports_comma_and_range():
    assert parse_interval_value("0,5") == 0.5
    assert parse_interval_value("3") == 3
    assert parse_interval_value("0.24") is None
    assert parse_interval_value("169") is None
    assert parse_interval_value("abc") is None
