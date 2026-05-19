from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.keyboards import settings_menu, user_menu
from bot.services.channels import deactivate_channel, get_channel_settings, has_user_channel, list_user_channels, update_channel_field
from bot.services.schedules import clear_channel_schedule, get_channel_schedule, replace_channel_schedule
from bot.states import CreatePostState
from bot.handlers.batch_schedule import _default_slots, _format_schedule, _parse_schedule

router = Router()


@router.message(F.text == '⚙️ Настройки')
async def open_settings(message: Message):
    await message.answer('Настройки:', reply_markup=settings_menu())


@router.message(F.text == '📣 Каналы')
async def channels_settings(message: Message, config):
    rows = await list_user_channels(config.database_path, message.from_user.id, only_active=True)
    text = 'Активные каналы:\n' + ('\n'.join(f'- {title or "Без названия"}' for _, title, *_ in rows) if rows else 'Нет каналов.')
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='➕ Добавить канал', callback_data='settings_add_channel')],
        [InlineKeyboardButton(text='📋 Список каналов', callback_data='set_channels_list')],
        [InlineKeyboardButton(text='❌ Удалить/отключить канал', callback_data='set_channels_disable')],
        [InlineKeyboardButton(text='🧪 Проверить доступ', callback_data='set_channels_check')],
    ])
    await message.answer(text, reply_markup=kb)




@router.callback_query(F.data == 'settings_add_channel')
async def settings_add_channel(call: CallbackQuery, state: FSMContext):
    from bot.states import AddChannelState
    await state.set_state(AddChannelState.waiting_channel_ref)
    await call.message.answer(
        '1. Добавьте этого бота в ваш канал.\n'
        '2. Выдайте ему права администратора.\n'
        '3. Разрешите публиковать сообщения.\n'
        '4. Отправьте username канала, например @my_channel.'
    )
    await call.answer()

@router.callback_query(F.data == 'set_channels_list')
async def set_channels_list(call: CallbackQuery, config):
    rows = await list_user_channels(config.database_path, call.from_user.id, only_active=True)
    if not rows:
        await call.message.answer('Нет активных каналов.')
    else:
        await call.message.answer('Список каналов:\n' + '\n'.join(f'{i}. {title or "Без названия"}' for i, (_, title, *_ ) in enumerate(rows, 1)))
    await call.answer()


async def _channel_pick_kb(prefix: str, rows):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=(t or c), callback_data=f'{prefix}:{c}')] for c, t, *_ in rows])


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
        can_post = getattr(member, 'can_post_messages', True) is not False
        await call.message.answer(f'Проверка пройдена. Бот может публиковать: {"да" if can_post else "нет"}.')
    except Exception:
        await call.message.answer('Проверка не пройдена.')
    await call.answer()


@router.message(F.text == '🗓 Расписание каналов')
async def schedule_settings(message: Message, config):
    rows = await list_user_channels(config.database_path, message.from_user.id, only_active=True)
    if not rows:
        await message.answer('Нет активных каналов.')
        return
    await message.answer('Выберите канал:', reply_markup=await _channel_pick_kb('set_sched_ch', rows))


@router.callback_query(F.data.startswith('set_sched_ch:'))
async def set_sched_channel(call: CallbackQuery, config):
    cid = call.data.split(':', 1)[1]
    if not await has_user_channel(config.database_path, call.from_user.id, cid):
        await call.answer('Нет доступа', show_alert=True)
        return
    slots = await get_channel_schedule(config.database_path, call.from_user.id, cid)
    text = 'Текущее расписание:\n\n' + _format_schedule(slots or _default_slots())
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✏️ Изменить расписание', callback_data=f'set_sched_edit:{cid}')],
        [InlineKeyboardButton(text='🧹 Очистить расписание', callback_data=f'set_sched_clear:{cid}')],
    ])
    await call.message.answer(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith('set_sched_edit:'))
async def set_sched_edit(call: CallbackQuery, state: FSMContext):
    cid = call.data.split(':', 1)[1]
    await state.set_state(CreatePostState.waiting_settings_schedule_text)
    await state.update_data(settings_sched_channel=cid)
    await call.message.answer('Отправьте расписание в формате:\nПн: 11:00, 14:00\nВт: 12:00, 18:00')
    await call.answer()


@router.message(CreatePostState.waiting_settings_schedule_text)
async def set_sched_edit_apply(message: Message, state: FSMContext, config):
    cid = (await state.get_data()).get('settings_sched_channel')
    if not cid or not await has_user_channel(config.database_path, message.from_user.id, cid):
        await state.clear()
        return
    try:
        slots = _parse_schedule(message.text or '')
    except ValueError as e:
        await message.answer(str(e))
        return
    await replace_channel_schedule(config.database_path, message.from_user.id, cid, slots)
    await state.clear()
    await message.answer('Расписание обновлено.')


@router.callback_query(F.data.startswith('set_sched_clear:'))
async def set_sched_clear(call: CallbackQuery, config):
    cid = call.data.split(':', 1)[1]
    if not await has_user_channel(config.database_path, call.from_user.id, cid):
        await call.answer('Нет доступа', show_alert=True)
        return
    await clear_channel_schedule(config.database_path, call.from_user.id, cid)
    await call.message.answer('Расписание очищено.')
    await call.answer()


@router.message(F.text == '✍️ Автоподпись')
async def signature_settings(message: Message, config):
    rows = await list_user_channels(config.database_path, message.from_user.id, only_active=True)
    if not rows:
        await message.answer('Нет активных каналов.')
        return
    await message.answer('Выберите канал:', reply_markup=await _channel_pick_kb('set_sign_ch', rows))


@router.callback_query(F.data.startswith('set_sign_ch:'))
async def set_sign_ch(call: CallbackQuery, state: FSMContext, config):
    cid = call.data.split(':', 1)[1]
    if not await has_user_channel(config.database_path, call.from_user.id, cid):
        await call.answer('Нет доступа', show_alert=True)
        return
    st = await get_channel_settings(config.database_path, call.from_user.id, cid)
    current = (st or {}).get('signature') or 'не задана'
    await state.set_state(CreatePostState.waiting_settings_signature_text)
    await state.update_data(settings_sign_channel=cid)
    await call.message.answer(f'Текущая автоподпись: {current}\n\nОтправьте новую подпись. Для очистки: - или off')
    await call.answer()


@router.message(CreatePostState.waiting_settings_signature_text)
async def set_sign_apply(message: Message, state: FSMContext, config):
    cid = (await state.get_data()).get('settings_sign_channel')
    if not cid or not await has_user_channel(config.database_path, message.from_user.id, cid):
        await state.clear()
        return
    val = (message.text or '').strip()
    if val.lower() in {'-', 'off'}:
        val = None
    await update_channel_field(config.database_path, message.from_user.id, cid, 'signature', val)
    await state.clear()
    await message.answer('Автоподпись обновлена.')


@router.message(F.text == '⬅️ Назад')
async def back_main_from_settings(message: Message, config):
    is_owner = message.from_user.id in config.owner_ids
    await message.answer('Главное меню', reply_markup=user_menu(is_owner))
