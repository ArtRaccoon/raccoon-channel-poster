from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == '❓ Помощь')
async def help_menu(message: Message):
    await message.answer('Добавьте канал, создайте текст поста и опубликуйте его в один из ваших каналов.')
