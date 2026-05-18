from aiogram import Router
from aiogram.types import Message

from bot.storage import JsonStorage

router = Router()


@router.message(lambda msg: msg.text == "Статистика")
async def statistics(message: Message) -> None:
    storage: JsonStorage = message.bot["storage"]
    stats = storage.count_all()
    await message.answer(
        "Статистика:\n"
        f"Каналов: {stats['channels']}\n"
        f"Черновиков: {stats['drafts']}\n"
        f"Постов: {stats['posts']}"
    )
