from aiogram import Router
from aiogram.types import Message

router = Router()


@router.message(lambda msg: msg.text == "Черновики")
async def drafts_stub(message: Message) -> None:
    await message.answer("Черновики будут добавлены на следующем этапе.")
