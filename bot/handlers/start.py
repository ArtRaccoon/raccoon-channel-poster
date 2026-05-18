from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.keyboards import user_menu
from bot.services.users import upsert_user

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, config):
    await upsert_user(config.database_path, message.from_user.id, message.from_user.username, message.from_user.first_name)
    is_owner = message.from_user.id in config.owner_ids
    await message.answer('Привет! Я помогу публиковать посты в ваши Telegram-каналы.', reply_markup=user_menu(is_owner))
