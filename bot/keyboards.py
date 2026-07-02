from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def user_menu(is_owner: bool) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text='⚙️ Настройки')],
    ]
    if is_owner:
        rows.append([KeyboardButton(text='🛠 Админ-панель')])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📊 Статистика')],
            [KeyboardButton(text='📈 Отчёт за 24ч'), KeyboardButton(text='📈 Отчёт за 7д')],
            [KeyboardButton(text='👥 Пользователи')],
            [KeyboardButton(text='📣 Все каналы')],
            [KeyboardButton(text='🌐 Прокси-статус')],
            [KeyboardButton(text='💾 Бэкап базы'), KeyboardButton(text='🚨 Ошибки')],
            [KeyboardButton(text='🧾 Логи редактирования')],
            [KeyboardButton(text='⬅️ Назад')],
        ],
        resize_keyboard=True,
    )


def settings_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📣 Каналы')],
            [KeyboardButton(text='🔗 Полезные ссылки')],
            [KeyboardButton(text='✅ Автообработка: Вкл/Выкл')],
            [KeyboardButton(text='🧪 Тест редактирования')],
            [KeyboardButton(text='⬅️ Назад')],
        ],
        resize_keyboard=True,
    )
