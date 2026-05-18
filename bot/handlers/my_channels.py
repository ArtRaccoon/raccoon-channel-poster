from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.services.channels import deactivate_channel, list_user_channels

router = Router()


@router.message(F.text == '📋 Мои каналы')
async def show_channels(message: Message, config):
    rows = await list_user_channels(config.database_path, message.from_user.id, only_active=True)
    if not rows:
        await message.answer('У вас пока нет активных каналов.')
        return
    text = ['Ваши активные каналы:']
    kb = []
    for channel_id, title, username, _ in rows:
        uname = f'@{username}' if username else 'без username'
        text.append(f'- {title or "Без названия"} ({uname}, {channel_id})')
        kb.append([
            InlineKeyboardButton(text=f'Удалить {title or channel_id}', callback_data=f'ch_delete:{channel_id}'),
            InlineKeyboardButton(text='Проверить доступ', callback_data=f'ch_check:{channel_id}'),
        ])
    await message.answer('\n'.join(text), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data.startswith('ch_delete:'))
async def delete_channel(call: CallbackQuery, config):
    channel_id = call.data.split(':', 1)[1]
    await deactivate_channel(config.database_path, call.from_user.id, channel_id)
    await call.answer('Канал отключён')


@router.callback_query(F.data.startswith('ch_check:'))
async def check_channel(call: CallbackQuery, config, bot):
    channel_id = call.data.split(':', 1)[1]
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
