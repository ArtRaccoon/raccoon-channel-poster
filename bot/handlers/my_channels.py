from aiogram import Router, F
from aiogram.types import Message

from bot.services.channels import list_user_channels

router = Router()


@router.message(F.text == '📋 Мои каналы')
async def show_channels(message: Message, config):
    rows = await list_user_channels(config.database_path, message.from_user.id)
    if not rows:
        await message.answer('У вас пока нет добавленных каналов.')
        return
    text = ['Ваши каналы:']
    for channel_id, title, username, is_active in rows:
        uname = f'@{username}' if username else 'без username'
        text.append(f'- {title or "Без названия"} ({uname}, {channel_id}), active={is_active}')
    await message.answer('\n'.join(text))
