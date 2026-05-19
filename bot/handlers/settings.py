from aiogram import F, Router
from aiogram.types import Message

from bot.keyboards import settings_menu, user_menu

router = Router()


@router.message(F.text == '⚙️ Настройки')
async def open_settings(message: Message):
    await message.answer('Настройки:', reply_markup=settings_menu())


@router.message(F.text == '📣 Каналы')
async def channels_settings(message: Message):
    await message.answer('Каналы:\n➕ Добавить канал\n📋 Список каналов\n❌ Удалить/отключить канал\n🧪 Проверить доступ')


@router.message(F.text == '🗓 Расписание каналов')
async def schedule_settings(message: Message):
    await message.answer('Выберите канал через меню создания расписания и измените слоты в формате:\nПн: 11:00, 14:00, 17:00, 20:00')


@router.message(F.text == '✍️ Автоподпись')
async def signature_settings(message: Message):
    await message.answer('Выберите канал и отправьте новую автоподпись. Для очистки отправьте: - или off')


@router.message(F.text == '⬅️ Назад')
async def back_main_from_settings(message: Message, config):
    is_owner = message.from_user.id in config.owner_ids
    await message.answer('Главное меню', reply_markup=user_menu(is_owner))
