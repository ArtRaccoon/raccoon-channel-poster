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
    text = ['Ваши каналы:', '']
    for i, (_, title, _, _) in enumerate(rows, start=1):
        text.append(f'{i}. {title or "Без названия"}')
    kb = [[InlineKeyboardButton(text=(title or channel_id), callback_data=f'ch_menu:{channel_id}')] for channel_id, title, *_ in rows]
    await message.answer('\n'.join(text), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data.startswith('ch_menu:'))
async def channel_menu(call: CallbackQuery):
    cid = call.data.split(':', 1)[1]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='⚙️ Настроить канал', callback_data=f'ch_setup:{cid}')],
        [InlineKeyboardButton(text='🧪 Проверить доступ', callback_data=f'ch_check:{cid}')],
        [InlineKeyboardButton(text='❌ Отключить канал', callback_data=f'ch_delete:{cid}')],
    ])
    await call.message.answer('Действия с каналом:', reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith('ch_setup:'))
async def setup_channel(call: CallbackQuery):
    await call.answer()
    await call.message.answer('Откройте ⚙️ Настройки для изменения автоподписи и расписания.')


@router.callback_query(F.data.startswith('ch_delete:'))
async def delete_channel(call: CallbackQuery, config):
    channel_id = call.data.split(':', 1)[1]
    await deactivate_channel(config.database_path, call.from_user.id, channel_id)
    await call.message.answer('Канал отключён.')
    await call.answer('Отключено')


@router.callback_query(F.data.startswith('ch_check:'))
async def check_channel(call: CallbackQuery, config, bot):
    channel_id = call.data.split(':', 1)[1]
    try:
        chat = await bot.get_chat(channel_id)
        bot_member = await bot.get_chat_member(chat.id, bot.id)
        can_post = getattr(bot_member, 'can_post_messages', True) is not False
        await call.message.answer(f'Доступ к каналу проверен. Бот может публиковать: {"да" if can_post else "нет"}.')
    except Exception:
        await call.message.answer('Проверка не пройдена. Проверьте права бота и доступ к каналу.')
    await call.answer()
