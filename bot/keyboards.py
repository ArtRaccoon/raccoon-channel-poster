from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

MAIN_MENU_LABELS = [
    ["Создать пост", "Контент-план"],
    ["Изменить пост", "Статистика"],
    ["Черновики", "Настройки"],
]

SETTINGS_MENU_LABELS = [
    ["Добавить канал", "Список каналов"],
    ["Прокси-статус", "Назад"],
]


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=label) for label in row]
            for row in MAIN_MENU_LABELS
        ],
        resize_keyboard=True,
    )


def settings_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=label) for label in row]
            for row in SETTINGS_MENU_LABELS
        ],
        resize_keyboard=True,
    )
