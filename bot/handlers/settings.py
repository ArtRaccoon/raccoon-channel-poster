from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.keyboards import settings_menu, user_menu
from bot.services.channels import deactivate_channel, get_channel_settings, has_user_channel, list_user_channels, update_channel_field
from bot.services.link_injector import append_links_block
from bot.states import AddChannelState, CreatePostState

router = Router()


@router.message(F.text == '⚙️ Настройки')
async def open_settings(message: Message):
    await message.answer('Настройки:', reply_markup=settings_menu())


async def _channel_pick_kb(prefix: str, rows):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=(t or c), callback_data=f'{prefix}:{c}')] for c, t, *_ in rows])


@router.message(F.text == '📣 Каналы')
async def channels_settings(message: Message, config):
    rows = await list_user_channels(config.database_path, message.from_user.id, only_active=True)
    text = 'Активные каналы:\n' + ('\n'.join(f'- {title or "Без названия"}' for _, title, *_ in rows) if rows else 'Нет каналов.')
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='➕ Добавить канал', callback_data='settings_add_channel')],
        [InlineKeyboardButton(text='📋 Список каналов', callback_data='set_channels_list')],
        [InlineKeyboardButton(text='❌ Отключить канал', callback_data='set_channels_disable')],
        [InlineKeyboardButton(text='🧪 Проверить права', callback_data='set_channels_check')],
    ])
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == 'settings_add_channel')
async def settings_add_channel(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddChannelState.waiting_channel_ref)
    await call.message.answer(
        '1. Добавьте этого бота в ваш канал.\n'
        '2. Выдайте ему права администратора и право редактирования сообщений.\n'
        '3. Отправьте username канала, например @my_channel.'
    )
    await call.answer()


@router.callback_query(F.data == 'set_channels_list')
async def set_channels_list(call: CallbackQuery, config):
    rows = await list_user_channels(config.database_path, call.from_user.id, only_active=True)
    if not rows:
        await call.message.answer('Нет активных каналов.')
    else:
        lines = ['Список каналов:']
        for i, (cid, title, username, _, auto_edit) in enumerate(rows, 1):
            lines.append(f'{i}. {title or "Без названия"} | {username or cid} | автообработка={"вкл" if auto_edit else "выкл"}')
        await call.message.answer('\n'.join(lines))
    await call.answer()


@router.callback_query(F.data == 'set_channels_disable')
async def set_channels_disable(call: CallbackQuery, config):
    rows = await list_user_channels(config.database_path, call.from_user.id, only_active=True)
    if not rows:
        await call.message.answer('Нет активных каналов.')
    else:
        await call.message.answer('Выберите канал для отключения:', reply_markup=await _channel_pick_kb('set_ch_disable', rows))
    await call.answer()


@router.callback_query(F.data.startswith('set_ch_disable:'))
async def set_ch_disable_apply(call: CallbackQuery, config):
    cid = call.data.split(':', 1)[1]
    if not await has_user_channel(config.database_path, call.from_user.id, cid):
        await call.answer('Нет доступа', show_alert=True)
        return
    await deactivate_channel(config.database_path, call.from_user.id, cid)
    await call.message.answer('Канал отключён.')
    await call.answer()


@router.callback_query(F.data == 'set_channels_check')
async def set_channels_check(call: CallbackQuery, config):
    rows = await list_user_channels(config.database_path, call.from_user.id, only_active=True)
    if not rows:
        await call.message.answer('Нет активных каналов.')
    else:
        await call.message.answer('Выберите канал для проверки:', reply_markup=await _channel_pick_kb('set_ch_check', rows))
    await call.answer()


@router.callback_query(F.data.startswith('set_ch_check:'))
async def set_ch_check_apply(call: CallbackQuery, config, bot):
    cid = call.data.split(':', 1)[1]
    if not await has_user_channel(config.database_path, call.from_user.id, cid):
        await call.answer('Нет доступа', show_alert=True)
        return
    try:
        chat = await bot.get_chat(cid)
        member = await bot.get_chat_member(chat.id, bot.id)
        is_admin = member.status in ('administrator', 'creator')
        can_edit = getattr(member, 'can_edit_messages', False) is True or member.status == 'creator'
        can_post = getattr(member, 'can_post_messages', False) is True or member.status == 'creator'
        if not is_admin:
            await call.message.answer('Бот добавлен, но не является администратором канала.')
        elif not can_edit:
            await call.message.answer('Бот добавлен, но не может редактировать посты. Выдайте право редактирования сообщений.')
        else:
            await call.message.answer(f'Проверка пройдена. Бот администратор, может редактировать посты. Право публикации: {"есть" if can_post else "нет"}.')
    except Exception:
        await call.message.answer('Проверка не пройдена.')
    await call.answer()


@router.message(F.text == '🔗 Полезные ссылки')
async def links_settings(message: Message, config):
    rows = await list_user_channels(config.database_path, message.from_user.id, only_active=True)
    if not rows:
        await message.answer('Нет активных каналов.')
        return
    await message.answer('Выберите канал для настройки ссылок:', reply_markup=await _channel_pick_kb('set_links_ch', rows))


@router.callback_query(F.data.startswith('set_links_ch:'))
async def set_links_channel(call: CallbackQuery, state: FSMContext, config):
    cid = call.data.split(':', 1)[1]
    if not await has_user_channel(config.database_path, call.from_user.id, cid):
        await call.answer('Нет доступа', show_alert=True)
        return
    settings = await get_channel_settings(config.database_path, call.from_user.id, cid)
    current = (settings or {}).get('links_block') or 'не задан'
    await state.set_state(CreatePostState.waiting_links_block_text)
    await state.update_data(settings_links_channel=cid)
    await call.message.answer(f'Текущий блок ссылок:\n{current}\n\nОтправьте новый блок. Для очистки: - или off')
    await call.answer()


@router.message(CreatePostState.waiting_links_block_text)
async def set_links_apply(message: Message, state: FSMContext, config):
    cid = (await state.get_data()).get('settings_links_channel')
    if not cid or not await has_user_channel(config.database_path, message.from_user.id, cid):
        await state.clear()
        return
    val = (message.text or '').strip()
    if val.lower() in {'-', 'off'}:
        val = None
    await update_channel_field(config.database_path, message.from_user.id, cid, 'links_block', val)
    await state.clear()
    await message.answer('Блок полезных ссылок обновлён.')


@router.message(F.text == '✅ Автообработка: Вкл/Выкл')
async def auto_edit_settings(message: Message, config):
    rows = await list_user_channels(config.database_path, message.from_user.id, only_active=True)
    if not rows:
        await message.answer('Нет активных каналов.')
        return
    await message.answer('Выберите канал для переключения автообработки:', reply_markup=await _channel_pick_kb('set_auto_ch', rows))


@router.callback_query(F.data.startswith('set_auto_ch:'))
async def set_auto_toggle(call: CallbackQuery, config):
    cid = call.data.split(':', 1)[1]
    if not await has_user_channel(config.database_path, call.from_user.id, cid):
        await call.answer('Нет доступа', show_alert=True)
        return
    settings = await get_channel_settings(config.database_path, call.from_user.id, cid)
    new_value = 0 if (settings or {}).get('auto_edit_enabled') else 1
    await update_channel_field(config.database_path, call.from_user.id, cid, 'auto_edit_enabled', new_value)
    await call.message.answer(f'Автообработка: {"включена" if new_value else "выключена"}.')
    await call.answer()


@router.message(F.text == '🧪 Тест редактирования')
async def test_render_settings(message: Message, config):
    rows = await list_user_channels(config.database_path, message.from_user.id, only_active=True)
    if not rows:
        await message.answer('Нет активных каналов.')
        return
    await message.answer('Выберите канал для тестовой сборки блока:', reply_markup=await _channel_pick_kb('set_test_ch', rows))


@router.callback_query(F.data.startswith('set_test_ch:'))
async def set_test_render(call: CallbackQuery, config):
    cid = call.data.split(':', 1)[1]
    if not await has_user_channel(config.database_path, call.from_user.id, cid):
        await call.answer('Нет доступа', show_alert=True)
        return
    settings = await get_channel_settings(config.database_path, call.from_user.id, cid)
    rendered = append_links_block('Пример поста', (settings or {}).get('links_block') or '')
    await call.message.answer(rendered if rendered != 'Пример поста' else 'Блок ссылок не задан.', parse_mode='HTML')
    await call.answer()


@router.message(F.text == '⬅️ Назад')
async def back_main_from_settings(message: Message, config):
    is_owner = message.from_user.id in config.owner_ids
    await message.answer('Главное меню', reply_markup=user_menu(is_owner))
