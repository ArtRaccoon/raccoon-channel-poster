from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def user_menu(is_owner: bool) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text='➕ Добавить канал')],
        [KeyboardButton(text='📋 Мои каналы')],
        [KeyboardButton(text='✍️ Создать пост')],
        [KeyboardButton(text='📝 Черновики'), KeyboardButton(text='🕘 Последние посты')],
        [KeyboardButton(text='🗓 Расписание'), KeyboardButton(text='📅 Контент-план')],
        [KeyboardButton(text='🧩 Шаблоны'), KeyboardButton(text='🔎 Поиск постов')],
        [KeyboardButton(text='❓ Помощь')],
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
            [KeyboardButton(text='📣 Каналы')],
            [KeyboardButton(text='🌐 Прокси-статус')],
            [KeyboardButton(text='💾 Бэкап базы'), KeyboardButton(text='🚨 Ошибки')],
            [KeyboardButton(text='⬅️ Назад')],
        ],
        resize_keyboard=True,
    )


def post_actions_inline(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ Опубликовать', callback_data=f'post_publish:{post_id}')],
        [InlineKeyboardButton(text='✏️ Редактировать текст', callback_data=f'post_edit:{post_id}')],
        [InlineKeyboardButton(text='📣 Выбрать канал', callback_data=f'post_choose_channel:{post_id}')],
        [InlineKeyboardButton(text='🔗 URL-кнопки', callback_data=f'post_buttons:{post_id}')],
        [InlineKeyboardButton(text='🖼 Заменить медиа', callback_data=f'post_replace_media:{post_id}')],
        [InlineKeyboardButton(text='📄 Дублировать', callback_data=f'post_duplicate:{post_id}')],
        [InlineKeyboardButton(text='💾 Оставить в черновиках', callback_data=f'post_keep:{post_id}')],
        [InlineKeyboardButton(text='🕒 Запланировать', callback_data=f'post_schedule:{post_id}')],
        [InlineKeyboardButton(text='❌ Отменить', callback_data=f'post_cancel:{post_id}')],
    ])
