from aiogram import F, Router
from aiogram.types import Message

router = Router()


@router.message(F.text == '🗓 Запланировать контент')
async def batch_mode(message: Message):
    await message.answer('Режим пакетной загрузки: выберите канал и загрузите контент. Функция включена в MVP и будет расширяться.')
