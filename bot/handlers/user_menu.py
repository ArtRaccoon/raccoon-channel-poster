from aiogram import Router, F
from aiogram.types import Message

from bot.keyboards import admin_menu, user_menu

router = Router()


@router.message(F.text == '🛠 Админ-панель')
async def open_admin(message: Message, config):
    if message.from_user.id not in config.owner_ids:
        return
    await message.answer('Админ-панель', reply_markup=admin_menu())


@router.message(F.text == '⬅️ Назад')
async def back_menu(message: Message, config):
    is_owner = message.from_user.id in config.owner_ids
    await message.answer('Главное меню', reply_markup=user_menu(is_owner))
