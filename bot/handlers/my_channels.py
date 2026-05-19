from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.services.channels import deactivate_channel, has_user_channel, list_user_channels, set_channel_signature
from bot.states import ChannelSignatureState

router = Router()


@router.message(F.text == '📋 Мои каналы')
async def show_channels(message: Message, config):
    rows = await list_user_channels(config.database_path, message.from_user.id, only_active=True)
    if not rows:
        await message.answer('У вас пока нет активных каналов.')
        return
    text = ['Ваши активные каналы:']
    kb = []
    for channel_id, title, username, _, signature in rows:
        uname = f'@{username}' if username else 'без username'
        sign = 'есть' if signature else 'нет'
        text.append(f'- {title or "Без названия"} ({uname}, {channel_id}), подпись: {sign}')
        kb.append([
            InlineKeyboardButton(text=f'Удалить {title or channel_id}', callback_data=f'ch_delete:{channel_id}'),
            InlineKeyboardButton(text='Проверить доступ', callback_data=f'ch_check:{channel_id}'),
            InlineKeyboardButton(text='✍️ Подпись', callback_data=f'ch_signature:{channel_id}'),
        ])
    await message.answer('\n'.join(text), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data.startswith('ch_delete:'))
async def delete_channel(call: CallbackQuery, config):
    channel_id = call.data.split(':', 1)[1]
    if not await has_user_channel(config.database_path, call.from_user.id, channel_id):
        await call.answer('Нет доступа', show_alert=True)
        return
    await deactivate_channel(config.database_path, call.from_user.id, channel_id)
    await call.message.answer('Канал отключён. Откройте 📋 Мои каналы, чтобы увидеть актуальный список.')
    await call.answer('Отключено')


@router.callback_query(F.data.startswith('ch_signature:'))
async def signature_start(call: CallbackQuery, state: FSMContext, config):
    channel_id = call.data.split(':', 1)[1]
    if not await has_user_channel(config.database_path, call.from_user.id, channel_id):
        await call.answer('Нет доступа', show_alert=True)
        return
    await state.set_state(ChannelSignatureState.waiting_signature)
    await state.update_data(signature_channel_id=channel_id)
    await call.message.answer('Отправьте текст подписи. Чтобы отключить подпись, отправьте - или off.')
    await call.answer()


@router.message(ChannelSignatureState.waiting_signature)
async def signature_apply(message: Message, state: FSMContext, config):
    data = await state.get_data()
    channel_id = data.get('signature_channel_id')
    if not channel_id or not await has_user_channel(config.database_path, message.from_user.id, channel_id):
        await state.clear()
        await message.answer('Канал недоступен.')
        return
    raw = (message.text or '').strip()
    signature = None if raw.lower() in ('-', 'off') else raw
    await set_channel_signature(config.database_path, message.from_user.id, channel_id, signature)
    await state.clear()
    await message.answer('Подпись очищена.' if signature is None else 'Подпись сохранена.')


@router.callback_query(F.data.startswith('ch_check:'))
async def check_channel(call: CallbackQuery, config, bot):
    channel_id = call.data.split(':', 1)[1]
    if not await has_user_channel(config.database_path, call.from_user.id, channel_id):
        await call.answer('Нет доступа', show_alert=True)
        return
    try:
        chat = await bot.get_chat(channel_id)
        bot_member = await bot.get_chat_member(chat.id, bot.id)
        user_member = await bot.get_chat_member(chat.id, call.from_user.id)
        can_post = getattr(bot_member, 'can_post_messages', True) is not False
        await call.message.answer(
            f'Канал доступен: да\n'
            f'Бот администратор: {"да" if bot_member.status in ("administrator", "creator") else "нет"}\n'
            f'Бот может публиковать: {"да" if can_post else "нет"}\n'
            f'Пользователь admin/creator: {"да" if user_member.status in ("administrator", "creator") else "нет"}'
        )
    except Exception as exc:
        await call.message.answer(f'Проверка не пройдена: {exc}')
    await call.answer()
