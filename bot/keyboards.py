from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def user_menu(is_owner: bool) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text='✍️ Создать пост')],
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
            [KeyboardButton(text='📣 Каналы')],
            [KeyboardButton(text='🌐 Прокси-статус')],
            [KeyboardButton(text='💾 Бэкап базы'), KeyboardButton(text='🚨 Ошибки')],
            [KeyboardButton(text='⬅️ Назад')],
        ],
        resize_keyboard=True,
    )


def create_post_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='🖼 Один пост')],
            [KeyboardButton(text='🗓 Расписание')],
            [KeyboardButton(text='⬅️ Назад')],
        ],
        resize_keyboard=True,
    )


def settings_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📣 Каналы')],
            [KeyboardButton(text='🗓 Расписание каналов')],
            [KeyboardButton(text='✍️ Автоподпись')],
            [KeyboardButton(text='⬅️ Назад')],
        ],
        resize_keyboard=True,
    )


def post_actions_inline(post_id: int, use_signature: bool = True, include_time_change: bool = False) -> InlineKeyboardMarkup:
    sign = 'Вкл' if use_signature else 'Выкл'
    rows = [
        [InlineKeyboardButton(text='👁 Предпросмотр', callback_data=f'post_preview:{post_id}')],
        [InlineKeyboardButton(text='✏️ Редактировать текст/подпись', callback_data=f'post_edit:{post_id}')],
        [InlineKeyboardButton(text='🖼 Заменить медиа', callback_data=f'post_media:{post_id}')],
        [InlineKeyboardButton(text=f'✍️ Автоподпись: {sign}', callback_data=f'post_signature_toggle:{post_id}')],
        [InlineKeyboardButton(text='✅ Опубликовать сейчас', callback_data=f'post_publish:{post_id}')],
        [InlineKeyboardButton(text='🕒 Опубликовать позже', callback_data=f'post_schedule:{post_id}')],
        [InlineKeyboardButton(text='💾 Сохранить как черновик', callback_data=f'post_keep:{post_id}')],
        [InlineKeyboardButton(text='❌ Отменить', callback_data=f'post_cancel:{post_id}')],
    ]
    if include_time_change:
        rows.insert(5, [InlineKeyboardButton(text='🕒 Изменить время', callback_data=f'post_schedule:{post_id}')])
    return InlineKeyboardMarkup(inline_keyboard=rows)
