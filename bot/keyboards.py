from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def user_menu(is_owner: bool) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text='➕ Добавить канал')],
        [KeyboardButton(text='📋 Мои каналы')],
        [KeyboardButton(text='✍️ Создать пост')],
        [KeyboardButton(text='❓ Помощь')],
    ]
    if is_owner:
        rows.append([KeyboardButton(text='🛠 Админ-панель')])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📊 Статистика')],
            [KeyboardButton(text='👥 Пользователи')],
            [KeyboardButton(text='📣 Каналы')],
            [KeyboardButton(text='🌐 Прокси-статус')],
            [KeyboardButton(text='⬅️ Назад')],
        ],
        resize_keyboard=True,
    )
