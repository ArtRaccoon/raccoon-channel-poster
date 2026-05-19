import json
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.keyboards import post_actions_inline, user_menu
from bot.services.channels import has_user_channel, list_user_channels
from bot.services.posts import (
    CAPTION_LIMIT,
    create_draft,
    create_post_copy,
    delete_draft,
    delete_old_drafts,
    get_post,
    list_recent_posts,
    search_posts,
    set_post_channel,
    set_post_status,
    update_post_buttons,
    update_post_media,
    update_post_text,
)
from bot.services.publishing import render_post_preview, publish_post
from bot.states import CreatePostState

router = Router()


def _preview(media_type: str | None, text: str | None) -> str:
    p = (text or '').strip().replace('\n', ' ')
    p = p if len(p) <= 80 else f'{p[:77]}...'
    if media_type == 'photo':
        return f'type=photo, preview={p or "<без подписи>"}'
    return f'type=text, preview={p or "<пусто>"}'


def _parse_url_buttons(raw: str) -> str:
    buttons = []
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines:
        raise ValueError('Отправьте хотя бы одну кнопку.')
    if len(lines) > 8:
        raise ValueError('Можно добавить максимум 8 кнопок.')
    for line in lines:
        if '|' not in line:
            raise ValueError('Каждая строка должна содержать разделитель |')
        text, url = [part.strip() for part in line.split('|', 1)]
        if not text:
            raise ValueError('Текст кнопки не должен быть пустым.')
        if not (url.startswith('http://') or url.startswith('https://')):
            raise ValueError('URL должен начинаться с http:// или https://')
        buttons.append({'text': text, 'url': url})
    return json.dumps(buttons, ensure_ascii=False)


def _channel_buttons(post_id: int, channels: list[tuple], prefix: str = 'ch_select') -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=(title or channel_id), callback_data=f'{prefix}:{post_id}:{channel_id}')]
        for channel_id, title, _, _, _ in channels
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def _show_post_preview(target: Message | CallbackQuery, post: tuple, bot, config):
    chat_id = target.chat.id if isinstance(target, Message) else target.from_user.id
    sender = target if isinstance(target, Message) else target.message
    try:
        await render_post_preview(bot, chat_id, post, config.database_path)
    except ValueError as exc:
        await sender.answer(str(exc))
    await sender.answer(
        f'Пост #{post[0]}\nstatus={post[6]}\nchannel={post[2] or "-"}\ncreated_at={post[7]}\nscheduled_at={post[9] or "-"}',
        reply_markup=post_actions_inline(post[0], post[6], has_channel=bool(post[2]), media_type=post[5]),
    )


async def _open_owned_post(config, post_id: int, user_id: int):
    post = await get_post(config.database_path, post_id)
    return post if post and post[1] == user_id else None


@router.message(F.text == '✍️ Создать пост')
async def create_post_start(message: Message, state: FSMContext):
    await state.set_state(CreatePostState.waiting_content)
    await message.answer('Отправьте текст или фото. Можно отправить фото с подписью.')


@router.message(CreatePostState.waiting_content)
async def receive_post_content(message: Message, state: FSMContext, config):
    channels = await list_user_channels(config.database_path, message.from_user.id, only_active=True)
    if not channels:
        await message.answer('Сначала добавьте хотя бы один активный канал.')
        await state.clear()
        return

    media_type = 'text'
    media_file_id = None
    text = message.text
    if message.photo:
        media_type = 'photo'
        media_file_id = message.photo[-1].file_id
        text = message.caption
    if media_type == 'photo' and text and len(text) > CAPTION_LIMIT:
        await message.answer('Подпись к фото не должна быть длиннее 1024 символов.')
        return
    if media_type == 'text' and not text:
        await message.answer('Отправьте текст или фото. Можно отправить фото с подписью.')
        return

    post_id = await create_draft(config.database_path, message.from_user.id, text, media_file_id, media_type)
    await state.update_data(post_id=post_id)
    await state.set_state(CreatePostState.waiting_channel)
    await message.answer('Черновик создан. Выберите канал:', reply_markup=_channel_buttons(post_id, channels))


@router.callback_query(F.data.startswith('ch_select:'))
async def choose_channel(call: CallbackQuery, bot, config):
    _, post_id, channel_id = call.data.split(':', 2)
    post = await _open_owned_post(config, int(post_id), call.from_user.id)
    if not post:
        await call.answer('Нет доступа', show_alert=True)
        return
    if not await has_user_channel(config.database_path, call.from_user.id, channel_id):
        await call.answer('Канал недоступен', show_alert=True)
        return
    await set_post_channel(config.database_path, int(post_id), channel_id)
    await call.answer('Канал выбран')
    post = await get_post(config.database_path, int(post_id))
    await _show_post_preview(call, post, bot, config)


@router.message(F.text == '📝 Черновики')
async def show_drafts(message: Message, config):
    rows = await list_recent_posts(config.database_path, message.from_user.id, only_drafts=True)
    kb_rows = [[InlineKeyboardButton(text='🧹 Очистить старые черновики', callback_data='drafts_cleanup_confirm')]]
    if not rows:
        await message.answer('Черновиков нет.', reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
        return
    text = ['Последние 10 черновиков:']
    for post_id, media_type, post_text, _, created_at in rows:
        text.append(f'#{post_id} | {_preview(media_type, post_text)} | {created_at}')
        kb_rows.append([
            InlineKeyboardButton(text=f'Открыть #{post_id}', callback_data=f'draft_open:{post_id}'),
            InlineKeyboardButton(text='Удалить', callback_data=f'draft_delete:{post_id}'),
        ])
    await message.answer('\n'.join(text), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))


@router.message(F.text == '🕘 Последние посты')
async def show_recent_posts(message: Message, config):
    rows = await list_recent_posts(config.database_path, message.from_user.id, only_drafts=False)
    if not rows:
        await message.answer('Постов пока нет.')
        return
    kb_rows = []
    text = ['Последние 10 постов:']
    for post_id, media_type, post_text, status, created_at in rows:
        text.append(f'#{post_id} | {status} | {_preview(media_type, post_text)} | {created_at}')
        kb_rows.append([InlineKeyboardButton(text=f'Открыть #{post_id}', callback_data=f'draft_open:{post_id}')])
    await message.answer('\n'.join(text), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))


@router.message(F.text == '🔎 Поиск постов')
async def search_start(message: Message, state: FSMContext):
    await state.set_state(CreatePostState.waiting_search_query)
    await message.answer('Отправьте поисковый запрос.')


@router.message(CreatePostState.waiting_search_query)
async def search_apply(message: Message, state: FSMContext, config):
    query = (message.text or '').strip()
    if not query:
        await message.answer('Запрос не должен быть пустым.')
        return
    rows = await search_posts(config.database_path, message.from_user.id, query)
    await state.clear()
    if not rows:
        await message.answer('Совпадений не найдено.')
        return
    text = [f'Найдено совпадений: {len(rows)}']
    kb_rows = []
    for post_id, media_type, post_text, status, _ in rows:
        text.append(f'#{post_id} | {status} | {media_type} | {_preview(media_type, post_text)}')
        kb_rows.append([InlineKeyboardButton(text=f'Открыть #{post_id}', callback_data=f'draft_open:{post_id}')])
    await message.answer('\n'.join(text), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))


@router.callback_query(F.data.startswith('draft_open:'))
async def open_draft(call: CallbackQuery, bot, config):
    post_id = int(call.data.split(':')[1])
    post = await _open_owned_post(config, post_id, call.from_user.id)
    if not post:
        await call.answer('Нет доступа', show_alert=True)
        return
    await call.answer()
    await _show_post_preview(call, post, bot, config)


@router.callback_query(F.data == 'draft_back')
async def draft_back(call: CallbackQuery):
    await call.answer()
    await call.message.answer('Откройте раздел 📝 Черновики в меню.')


@router.callback_query(F.data.startswith('draft_delete:'))
async def remove_draft(call: CallbackQuery, config):
    post_id = int(call.data.split(':')[1])
    await delete_draft(config.database_path, post_id, call.from_user.id)
    await call.answer('Удалено')


@router.callback_query(F.data == 'drafts_cleanup_confirm')
async def drafts_cleanup_confirm(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ Да, удалить старые', callback_data='drafts_cleanup_yes')],
        [InlineKeyboardButton(text='❌ Нет', callback_data='drafts_cleanup_no')],
    ])
    await call.message.answer('Удалить черновики старше 30 дней?', reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == 'drafts_cleanup_no')
async def drafts_cleanup_no(call: CallbackQuery):
    await call.answer('Отменено')


@router.callback_query(F.data == 'drafts_cleanup_yes')
async def drafts_cleanup_yes(call: CallbackQuery, config):
    count = await delete_old_drafts(config.database_path, call.from_user.id)
    await call.message.answer(f'Удалено старых черновиков: {count}')
    await call.answer('Готово')


@router.callback_query(F.data.startswith('post_edit:'))
async def start_edit(call: CallbackQuery, state: FSMContext, config):
    post_id = int(call.data.split(':')[1])
    post = await _open_owned_post(config, post_id, call.from_user.id)
    if not post:
        await call.answer('Нет доступа', show_alert=True)
        return
    await state.set_state(CreatePostState.waiting_edit_text)
    await state.update_data(edit_post_id=post_id)
    await call.answer()
    await call.message.answer('Отправьте новый текст.')


@router.message(CreatePostState.waiting_edit_text)
async def apply_edit(message: Message, state: FSMContext, bot, config):
    data = await state.get_data()
    post_id = int(data.get('edit_post_id'))
    post = await _open_owned_post(config, post_id, message.from_user.id)
    if not post:
        await state.clear()
        return
    new_text = message.text or ''
    if post[5] == 'photo' and len(new_text) > CAPTION_LIMIT:
        await message.answer('Подпись к фото не должна быть длиннее 1024 символов.')
        return
    await update_post_text(config.database_path, post_id, new_text)
    await state.clear()
    updated = await get_post(config.database_path, post_id)
    await _show_post_preview(message, updated, bot, config)


@router.callback_query(F.data.startswith('post_buttons:'))
async def start_buttons(call: CallbackQuery, state: FSMContext, config):
    post_id = int(call.data.split(':')[1])
    post = await _open_owned_post(config, post_id, call.from_user.id)
    if not post:
        await call.answer('Нет доступа', show_alert=True)
        return
    await state.set_state(CreatePostState.waiting_buttons)
    await state.update_data(buttons_post_id=post_id)
    await call.answer()
    await call.message.answer('Отправьте кнопки в формате:\nТекст кнопки | https://example.com\nТекст кнопки 2 | https://example.org\n\nМожно несколько строк, максимум 8.')


@router.message(CreatePostState.waiting_buttons)
async def apply_buttons(message: Message, state: FSMContext, bot, config):
    data = await state.get_data()
    post_id = int(data['buttons_post_id'])
    post = await _open_owned_post(config, post_id, message.from_user.id)
    if not post:
        await state.clear()
        return
    try:
        buttons_json = _parse_url_buttons(message.text or '')
    except ValueError as exc:
        await message.answer(str(exc))
        return
    await update_post_buttons(config.database_path, post_id, message.from_user.id, buttons_json)
    await state.clear()
    await message.answer('URL-кнопки сохранены.')
    updated = await get_post(config.database_path, post_id)
    await _show_post_preview(message, updated, bot, config)


@router.callback_query(F.data.startswith('post_replace_photo:'))
async def start_replace_photo(call: CallbackQuery, state: FSMContext, config):
    post_id = int(call.data.split(':')[1])
    post = await _open_owned_post(config, post_id, call.from_user.id)
    if not post:
        await call.answer('Нет доступа', show_alert=True)
        return
    await state.set_state(CreatePostState.waiting_replace_photo)
    await state.update_data(replace_photo_post_id=post_id)
    await call.answer()
    await call.message.answer('Отправьте новое фото.')


@router.message(CreatePostState.waiting_replace_photo)
async def apply_replace_photo(message: Message, state: FSMContext, bot, config):
    data = await state.get_data()
    post_id = int(data['replace_photo_post_id'])
    post = await _open_owned_post(config, post_id, message.from_user.id)
    if not post:
        await state.clear()
        return
    if not message.photo:
        await message.answer('Нужно отправить фото.')
        return
    if post[5] != 'photo' and post[3] and len(post[3]) > CAPTION_LIMIT:
        await message.answer('Сначала сократите текст до 1024 символов, чтобы превратить пост в фото-пост.')
        return
    await update_post_media(config.database_path, post_id, message.from_user.id, message.photo[-1].file_id, 'photo')
    await state.clear()
    updated = await get_post(config.database_path, post_id)
    await message.answer('Фото обновлено.')
    await _show_post_preview(message, updated, bot, config)


@router.callback_query(F.data.startswith('post_duplicate:'))
async def duplicate_post(call: CallbackQuery, config):
    post_id = int(call.data.split(':')[1])
    post = await _open_owned_post(config, post_id, call.from_user.id)
    if not post:
        await call.answer('Нет доступа', show_alert=True)
        return
    new_id = await create_post_copy(config.database_path, post, status='draft')
    await call.message.answer(f'Создана копия поста #{new_id}')
    await call.answer('Создано')


@router.callback_query(F.data.startswith('post_republish:'))
async def republish_post(call: CallbackQuery, config):
    post_id = int(call.data.split(':')[1])
    post = await _open_owned_post(config, post_id, call.from_user.id)
    if not post:
        await call.answer('Нет доступа', show_alert=True)
        return
    if post[6] != 'published':
        await call.answer('Доступно только для опубликованных постов', show_alert=True)
        return
    new_id = await create_post_copy(config.database_path, post, channel_id=None, status='draft')
    channels = await list_user_channels(config.database_path, call.from_user.id, only_active=True)
    if not channels:
        await call.message.answer(f'Создан черновик #{new_id}, но активных каналов нет.')
        await call.answer()
        return
    await call.message.answer(f'Создан черновик #{new_id}. Выберите канал для перепубликации:', reply_markup=_channel_buttons(new_id, channels))
    await call.answer('Черновик создан')


@router.callback_query(F.data.startswith('post_choose_channel:'))
async def choose_channel_for_existing_draft(call: CallbackQuery, config):
    post_id = int(call.data.split(':')[1])
    post = await _open_owned_post(config, post_id, call.from_user.id)
    if not post:
        await call.answer('Нет доступа', show_alert=True)
        return
    channels = await list_user_channels(config.database_path, call.from_user.id, only_active=True)
    if not channels:
        await call.answer('Нет активных каналов', show_alert=True)
        return
    await call.message.answer('Выберите канал:', reply_markup=_channel_buttons(post_id, channels))
    await call.answer()


@router.callback_query(F.data.startswith('post_keep:'))
async def keep_draft(call: CallbackQuery):
    await call.answer('Оставлено в черновиках')


@router.callback_query(F.data.startswith('post_cancel:'))
async def cancel_post(call: CallbackQuery, config):
    post_id = int(call.data.split(':')[1])
    post = await _open_owned_post(config, post_id, call.from_user.id)
    if not post:
        await call.answer('Нет доступа', show_alert=True)
        return
    if post[6] == 'draft':
        await delete_draft(config.database_path, post_id, call.from_user.id)
        await call.message.answer('Черновик удалён.')
        await call.answer('Удалено')
    else:
        await call.message.answer('Пост уже нельзя отменить.')
        await call.answer('Недоступно')


@router.callback_query(F.data.startswith('post_schedule:'))
async def schedule_start(call: CallbackQuery, state: FSMContext, config):
    post_id = int(call.data.split(':')[1])
    post = await _open_owned_post(config, post_id, call.from_user.id)
    if not post:
        await call.answer('Нет доступа', show_alert=True)
        return
    if not post[2]:
        await call.answer('Сначала выберите канал для поста.', show_alert=True)
        return
    await state.set_state(CreatePostState.waiting_schedule_at)
    await state.update_data(schedule_post_id=post_id)
    await call.answer()
    await call.message.answer('Отправьте дату и время в формате ДД.ММ.ГГГГ ЧЧ:ММ')


@router.message(CreatePostState.waiting_schedule_at)
async def schedule_apply(message: Message, state: FSMContext, config):
    data = await state.get_data()
    post_id = int(data['schedule_post_id'])
    post = await _open_owned_post(config, post_id, message.from_user.id)
    if not post:
        await state.clear()
        return
    if not post[2] or not await has_user_channel(config.database_path, message.from_user.id, str(post[2])):
        await state.clear()
        await message.answer('Канал для поста не выбран или уже отключён. Выберите канал заново.')
        return
    try:
        dt = datetime.strptime(message.text.strip(), '%d.%m.%Y %H:%M').replace(tzinfo=ZoneInfo(config.timezone))
    except Exception:
        await message.answer('Неверный формат. Используйте ДД.ММ.ГГГГ ЧЧ:ММ')
        return
    await set_post_status(config.database_path, post_id, 'scheduled', scheduled_at=dt.astimezone(ZoneInfo('UTC')).isoformat())
    await state.clear()
    await message.answer(f'Пост запланирован на {dt.strftime("%d.%m.%Y %H:%M")}.')


@router.callback_query(F.data.startswith('post_publish:'))
async def publish_now(call: CallbackQuery, bot, config):
    post_id = int(call.data.split(':')[1])
    post = await _open_owned_post(config, post_id, call.from_user.id)
    if not post:
        await call.answer('Нет доступа', show_alert=True)
        return
    if not post[2] or not await has_user_channel(config.database_path, call.from_user.id, str(post[2])):
        await call.answer('Сначала выберите канал для поста.', show_alert=True)
        return
    ok, message_text = await publish_post(config.database_path, bot, post)
    await call.message.answer(message_text, reply_markup=user_menu(call.from_user.id in config.owner_ids) if ok else None)
    await call.answer()
