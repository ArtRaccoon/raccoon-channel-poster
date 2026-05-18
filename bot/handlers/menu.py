from aiogram import Router
from aiogram.types import Message

router = Router()


@router.message(lambda msg: msg.text == "Контент-план")
async def content_plan_stub(message: Message) -> None:
    await message.answer("Контент-план будет добавлен на следующем этапе.")


@router.message(lambda msg: msg.text == "Изменить пост")
async def edit_post_stub(message: Message) -> None:
    await message.answer("Редактирование постов будет добавлено на следующем этапе.")
