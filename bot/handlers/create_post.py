from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.keyboards import post_actions_inline, user_menu
from bot.services.channels import has_user_channel, list_user_channels
from bot.services.posts import (
    CAPTION_LIMIT,
    add_publish_log,
    create_draft,
    delete_draft,
    get_post,
    list_recent_posts,
    set_post_channel,
    set_post_status,
    update_post_text,
)
from bot.states import CreatePostState

router = Router()


def _preview(media_type: str | None, text: str | None) -> str:
    p = (text or '').strip()
    p = p if len(p) <= 80 else f'{p[:77]}...'
    if media_type == 'photo':
        return f'type=photo, preview={p or "<без подписи>"}'
    return f'type=text, preview={p or "<пусто>"}'


async def _show_post_preview(target: Message | CallbackQuery, post: tuple):
    _, _, channel_id, text, _, media_type, status, created_at, _, scheduled_at = post
    msg = (
        f'Пост #{post[0]}\nstatus={status}\nchannel={channel_id or "-"}\n'
        f'created_at={created_at}\nscheduled_at={scheduled_at or "-"}\n{_preview(media_type, text)}'
    )
    if isinstance(target, Message):
        await target.answer(msg, reply_markup=post_actions_inline(post[0]))
    else:
        await target.message.answer(msg, reply_markup=post_actions_inline(post[0]))


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

    buttons = [[InlineKeyboardButton(text=(title or channel_id), callback_data=f'ch_select:{post_id}:{channel_id}')] for channel_id, title, _, _ in channels]
    await message.answer('Черновик создан. Выберите канал:', reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith('ch_select:'))
async def choose_channel(call: CallbackQuery, config):
    _, post_id, channel_id = call.data.split(':', 2)
    post = await get_post(config.database_path, int(post_id))
    if not post or post[1] != call.from_user.id:
        await call.answer('Нет доступа', show_alert=True)
        return
    if not await has_user_channel(config.database_path, call.from_user.id, channel_id):
        await call.answer('Канал недоступен', show_alert=True)
        return
    await set_post_channel(config.database_path, int(post_id), channel_id)
    await call.answer('Канал выбран')
    post = await get_post(config.database_path, int(post_id))
    await _show_post_preview(call, post)


@router.message(F.text == '📝 Черновики')
async def show_drafts(message: Message, config):
    rows = await list_recent_posts(config.database_path, message.from_user.id, only_drafts=True)
    if not rows:
        await message.answer('Черновиков нет.')
        return
    kb_rows = []
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
    text = ['Последние 10 постов:']
    for post_id, media_type, post_text, status, created_at in rows:
        text.append(f'#{post_id} | {status} | {_preview(media_type, post_text)} | {created_at}')
    await message.answer('\n'.join(text))


@router.callback_query(F.data.startswith('draft_open:'))
async def open_draft(call: CallbackQuery, config):
    post_id = int(call.data.split(':')[1])
    post = await get_post(config.database_path, post_id)
    if not post or post[1] != call.from_user.id:
        await call.answer('Нет доступа', show_alert=True)
        return
    await call.answer()
    if post[2]:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='✅ Опубликовать', callback_data=f'post_publish:{post_id}')],
            [InlineKeyboardButton(text='✏️ Редактировать текст', callback_data=f'post_edit:{post_id}')],
            [InlineKeyboardButton(text='📣 Выбрать канал', callback_data=f'post_choose_channel:{post_id}')],
            [InlineKeyboardButton(text='🕒 Запланировать', callback_data=f'post_schedule:{post_id}')],
            [InlineKeyboardButton(text='🗑 Удалить', callback_data=f'draft_delete:{post_id}')],
            [InlineKeyboardButton(text='⬅️ Назад', callback_data='draft_back')],
        ])
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='📣 Выбрать канал', callback_data=f'post_choose_channel:{post_id}')],
            [InlineKeyboardButton(text='✏️ Редактировать текст', callback_data=f'post_edit:{post_id}')],
            [InlineKeyboardButton(text='🗑 Удалить', callback_data=f'draft_delete:{post_id}')],
            [InlineKeyboardButton(text='⬅️ Назад', callback_data='draft_back')],
        ])
    await call.message.answer(f'Черновик #{post_id}\n{_preview(post[5], post[3])}', reply_markup=kb)


@router.callback_query(F.data == 'draft_back')
async def draft_back(call: CallbackQuery):
    await call.answer()
    await call.message.answer('Откройте раздел 📝 Черновики в меню.')


@router.callback_query(F.data.startswith('draft_delete:'))
async def remove_draft(call: CallbackQuery, config):
    post_id = int(call.data.split(':')[1])
    await delete_draft(config.database_path, post_id, call.from_user.id)
    await call.answer('Удалено')


@router.callback_query(F.data.startswith('post_edit:'))
async def start_edit(call: CallbackQuery, state: FSMContext, config):
    post_id = int(call.data.split(':')[1])
    post = await get_post(config.database_path, post_id)
    if not post or post[1] != call.from_user.id:
        await call.answer('Нет доступа', show_alert=True)
        return
    await state.set_state(CreatePostState.waiting_edit_text)
    await state.update_data(edit_post_id=post_id)
    await call.answer()
    await call.message.answer('Отправьте новый текст.')


@router.message(CreatePostState.waiting_edit_text)
async def apply_edit(message: Message, state: FSMContext, config):
    data = await state.get_data()
    post_id = data.get('edit_post_id')
    post = await get_post(config.database_path, int(post_id))
    if not post or post[1] != message.from_user.id:
        await state.clear()
        return
    new_text = message.text or ''
    if post[5] == 'photo' and len(new_text) > CAPTION_LIMIT:
        await message.answer('Подпись к фото не должна быть длиннее 1024 символов.')
        return
    await update_post_text(config.database_path, int(post_id), new_text)
    await state.clear()
    updated = await get_post(config.database_path, int(post_id))
    await _show_post_preview(message, updated)



@router.callback_query(F.data.startswith('post_choose_channel:'))
async def choose_channel_for_existing_draft(call: CallbackQuery, config):
    post_id = int(call.data.split(':')[1])
    post = await get_post(config.database_path, post_id)
    if not post or post[1] != call.from_user.id:
        await call.answer('Нет доступа', show_alert=True)
        return
    channels = await list_user_channels(config.database_path, call.from_user.id, only_active=True)
    if not channels:
        await call.answer('Нет активных каналов', show_alert=True)
        return
    buttons = [[InlineKeyboardButton(text=(title or channel_id), callback_data=f'ch_select:{post_id}:{channel_id}')] for channel_id, title, _, _ in channels]
    await call.message.answer('Выберите канал:', reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await call.answer()


@router.callback_query(F.data.startswith('post_keep:'))
async def keep_draft(call: CallbackQuery):
    await call.answer('Оставлено в черновиках')


@router.callback_query(F.data.startswith('post_cancel:'))
async def cancel_post(call: CallbackQuery, config):
    post_id = int(call.data.split(':')[1])
    post = await get_post(config.database_path, post_id)
    if not post or post[1] != call.from_user.id:
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
    post = await get_post(config.database_path, post_id)
    if not post or post[1] != call.from_user.id:
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
    post = await get_post(config.database_path, post_id)
    if not post or post[1] != message.from_user.id:
        await state.clear()
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
    post = await get_post(config.database_path, post_id)
    if not post or post[1] != call.from_user.id:
        await call.answer('Нет доступа', show_alert=True)
        return
    if not post[2]:
        await call.answer('Сначала выберите канал для поста.', show_alert=True)
        return
    if not post[2] or not await has_user_channel(config.database_path, call.from_user.id, str(post[2])):
        await call.answer('Сначала выберите канал для поста.', show_alert=True)
        return
    try:
        if post[5] == 'photo':
            if post[3] and len(post[3]) > CAPTION_LIMIT:
                await call.message.answer('Подпись к фото не должна быть длиннее 1024 символов.')
                return
            await bot.send_photo(chat_id=post[2], photo=post[4], caption=post[3] or None)
        else:
            await bot.send_message(chat_id=post[2], text=post[3] or '')
        await set_post_status(config.database_path, post_id, 'published')
        await add_publish_log(config.database_path, call.from_user.id, post[2], post_id, 'success')
        await call.message.answer('Пост опубликован.', reply_markup=user_menu(call.from_user.id in config.owner_ids))
    except Exception as exc:
        await set_post_status(config.database_path, post_id, 'failed')
        await add_publish_log(config.database_path, call.from_user.id, post[2], post_id, 'error', str(exc))
        await call.message.answer(f'Ошибка публикации: {exc}')
    await call.answer()
