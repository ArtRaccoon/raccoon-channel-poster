import json
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.keyboards import post_actions_inline, user_menu
from bot.services.channels import get_channel_settings, has_user_channel, list_user_channels
from bot.services.posts import CAPTION_LIMIT, create_draft, delete_draft, get_post, list_recent_posts, set_post_channel, set_post_status, set_post_use_signature, update_post_media, update_post_text
from bot.services.publishing import build_post_text_with_signature, publish_post, render_post_preview
from bot.states import CreatePostState

router = Router()
ALBUM_BUFFER = {}


def _draft_row(post_id: int, media_type: str, channel_title: str, created_at: str) -> str:
    dt = datetime.fromisoformat(created_at)
    return f'#{post_id} — {media_type} — Канал: {channel_title} — {dt.strftime("%d %b %H:%M")}'


async def _show_preview(message: Message | CallbackQuery, post: tuple, channel: dict | None):
    ok, err = await render_post_preview(message.bot, message.from_user.id if isinstance(message, CallbackQuery) else message.from_user.id, post, channel)
    if not ok:
        target = message.message if isinstance(message, CallbackQuery) else message
        await target.answer(err)
    target = message.message if isinstance(message, CallbackQuery) else message
    await target.answer('Настройки поста:', reply_markup=post_actions_inline(post[0], bool(post[13] if len(post) > 13 else 1)))


@router.message(F.text == '✍️ Создать пост')
async def create_post_start(message: Message, state: FSMContext, config):
    channels = await list_user_channels(config.database_path, message.from_user.id, only_active=True)
    if not channels:
        await message.answer('Сначала добавьте хотя бы один активный канал.')
        return
    await state.set_state(CreatePostState.waiting_channel)
    kb = [[InlineKeyboardButton(text=(title or channel_id), callback_data=f'create_ch:{channel_id}')] for channel_id, title, *_ in channels]
    await message.answer('Выберите канал для публикации.', reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data.startswith('create_ch:'))
async def create_choose_channel(call: CallbackQuery, state: FSMContext):
    channel_id = call.data.split(':', 1)[1]
    await state.update_data(channel_id=channel_id)
    await state.set_state(CreatePostState.waiting_content)
    await call.message.answer('Отправьте пост: текст, фото или сгруппированные медиа.')
    await call.answer()


@router.message(CreatePostState.waiting_content)
async def receive_content(message: Message, state: FSMContext, config):
    data = await state.get_data()
    channel_id = data.get('channel_id')
    if not channel_id:
        await state.clear()
        return
    text = message.text
    media_type, media_file_id, media_json = 'text', None, None
    if message.media_group_id and message.photo:
        group = ALBUM_BUFFER.setdefault(message.media_group_id, [])
        group.append(message)
        return
    if message.photo:
        media_type, media_file_id, text = 'photo', message.photo[-1].file_id, message.caption
    if media_type == 'photo' and text and len(text) > CAPTION_LIMIT:
        await message.answer('Подпись к фото не должна быть длиннее 1024 символов.')
        return
    if media_type == 'text' and not text:
        await message.answer('Отправьте текст, фото или альбом.')
        return
    post_id = await create_draft(config.database_path, message.from_user.id, text, media_file_id, media_type, media_json)
    await set_post_channel(config.database_path, post_id, channel_id)
    await state.clear()
    post = await get_post(config.database_path, post_id)
    channel = await get_channel_settings(config.database_path, message.from_user.id, channel_id)
    await _show_preview(message, post, channel)


@router.message(F.media_group_id, CreatePostState.waiting_content)
async def receive_album(message: Message, state: FSMContext, config):
    group_id = message.media_group_id
    if group_id not in ALBUM_BUFFER:
        ALBUM_BUFFER[group_id] = []
    ALBUM_BUFFER[group_id].append(message)
    if len(ALBUM_BUFFER[group_id]) < 2:
        return
    data = await state.get_data()
    channel_id = data.get('channel_id')
    items = ALBUM_BUFFER.pop(group_id)
    if len(items) > 10:
        await message.answer('В альбоме может быть максимум 10 фото.')
        return
    media = [{"file_id": m.photo[-1].file_id} for m in items if m.photo]
    text = items[0].caption if items and items[0].caption else None
    if text and len(text) > CAPTION_LIMIT:
        await message.answer('Подпись к фото не должна быть длиннее 1024 символов.')
        return
    post_id = await create_draft(config.database_path, message.from_user.id, text, None, 'album', json.dumps(media), group_id)
    await set_post_channel(config.database_path, post_id, channel_id)
    await state.clear()
    post = await get_post(config.database_path, post_id)
    channel = await get_channel_settings(config.database_path, message.from_user.id, channel_id)
    await _show_preview(message, post, channel)


@router.message(F.text == '📝 Черновики')
async def show_drafts(message: Message, config):
    rows = await list_recent_posts(config.database_path, message.from_user.id, only_drafts=True)
    if not rows:
        await message.answer('Черновиков нет.')
        return
    channels = {c[0]: c[1] or c[0] for c in await list_user_channels(config.database_path, message.from_user.id, only_active=False)}
    text = ['Черновики:']
    kb = []
    for post_id, media_type, _, _, created_at in rows:
        post = await get_post(config.database_path, post_id)
        text.append(_draft_row(post_id, media_type, channels.get(post[2], 'Не выбран'), created_at))
        kb.append([InlineKeyboardButton(text=f'Открыть #{post_id}', callback_data=f'draft_open:{post_id}'), InlineKeyboardButton(text='Удалить', callback_data=f'draft_delete:{post_id}')])
    await message.answer('\n'.join(text), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data.startswith('draft_open:'))
async def open_draft(call: CallbackQuery, config):
    post_id = int(call.data.split(':')[1])
    post = await get_post(config.database_path, post_id)
    if not post or post[1] != call.from_user.id:
        await call.answer('Нет доступа', show_alert=True)
        return
    channel = await get_channel_settings(config.database_path, call.from_user.id, post[2]) if post[2] else None
    await _show_preview(call, post, channel)
    await call.answer()

@router.callback_query(F.data.startswith('post_signature_toggle:'))
async def toggle_signature(call: CallbackQuery, config):
    post_id = int(call.data.split(':')[1]); post = await get_post(config.database_path, post_id)
    await set_post_use_signature(config.database_path, post_id, 0 if post[13] else 1)
    post = await get_post(config.database_path, post_id)
    channel = await get_channel_settings(config.database_path, call.from_user.id, post[2]) if post[2] else None
    await _show_preview(call, post, channel)
    await call.answer('Обновлено')

@router.callback_query(F.data.startswith('post_media:'))
async def edit_media_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(CreatePostState.waiting_replace_media)
    await state.update_data(media_post_id=int(call.data.split(':')[1]))
    await call.message.answer('Отправьте новое фото или альбом.')
    await call.answer()

@router.message(CreatePostState.waiting_replace_media)
async def replace_media(message: Message, state: FSMContext, config):
    post_id = (await state.get_data()).get('media_post_id'); post = await get_post(config.database_path, int(post_id))
    if message.photo:
        await update_post_media(config.database_path, int(post_id), 'photo', media_file_id=message.photo[-1].file_id, media_json=None)
    else:
        await message.answer('Нужно отправить фото.')
        return
    await state.clear(); post = await get_post(config.database_path, int(post_id)); channel = await get_channel_settings(config.database_path, message.from_user.id, post[2]) if post[2] else None
    await _show_preview(message, post, channel)

@router.callback_query(F.data.startswith('post_keep:'))
async def keep_draft(call: CallbackQuery):
    await call.answer(); await call.message.answer('Пост сохранён в черновиках.')

@router.callback_query(F.data.startswith('draft_delete:'))
async def remove_draft(call: CallbackQuery, config):
    await delete_draft(config.database_path, int(call.data.split(':')[1]), call.from_user.id)
    await call.answer('Удалено')

@router.callback_query(F.data.startswith('post_schedule:'))
async def schedule_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(CreatePostState.waiting_schedule_at); await state.update_data(schedule_post_id=int(call.data.split(':')[1]))
    await call.message.answer('Отправьте дату и время в формате ДД.ММ.ГГГГ ЧЧ:ММ'); await call.answer()

@router.message(CreatePostState.waiting_schedule_at)
async def schedule_apply(message: Message, state: FSMContext, config):
    post_id = int((await state.get_data())['schedule_post_id']); post = await get_post(config.database_path, post_id)
    tz = (await get_channel_settings(config.database_path, message.from_user.id, post[2]) or {}).get('channel_timezone') or config.timezone
    dt = datetime.strptime(message.text.strip(), '%d.%m.%Y %H:%M').replace(tzinfo=ZoneInfo(tz))
    await set_post_status(config.database_path, post_id, 'scheduled', scheduled_at=dt.astimezone(ZoneInfo('UTC')).isoformat())
    await state.clear(); await message.answer(f'Пост запланирован на {dt.strftime("%d.%m.%Y %H:%M")}.')

@router.callback_query(F.data.startswith('post_publish:'))
async def publish_now(call: CallbackQuery, bot, config):
    ok, info = await publish_post(bot, config.database_path, int(call.data.split(':')[1]))
    await call.message.answer('Пост опубликован.' if ok else info, reply_markup=user_menu(call.from_user.id in config.owner_ids) if ok else None)
    await call.answer()
