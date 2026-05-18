from aiogram import Router
from aiogram.types import Message

router = Router()


@router.message(lambda msg: msg.text == "Создать пост")
async def create_post_stub(message: Message) -> None:
    await message.answer("Создание поста будет добавлено на следующем этапе.")
