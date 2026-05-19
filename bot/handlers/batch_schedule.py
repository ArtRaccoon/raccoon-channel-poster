from aiogram import F, Router
from aiogram.types import Message

router = Router()


@router.message(F.text == '🗓 Расписание')
async def batch_mode(message: Message):
    await message.answer(
        'Выберите канал в следующем шаге, затем отправьте расписание в формате:\n'
        'Пн: 11:00, 14:00, 17:00, 20:00\n'
        '...\n\n'
        'После подтверждения отправляйте медиа и завершите словом: готово'
    )
