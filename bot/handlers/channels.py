from aiogram import Router
from aiogram.types import Message

from bot.channels import get_channels
from bot.storage import JsonStorage

router = Router()


@router.message(lambda msg: msg.text == "Список каналов")
async def list_channels(message: Message) -> None:
    storage: JsonStorage = message.bot["storage"]
    channels = get_channels(storage)

    if not channels:
        await message.answer("Каналы пока не добавлены.")
        return

    lines = [
        f"{idx}. {item.get('title', 'Без названия')} ({item.get('chat_id', 'N/A')})"
        for idx, item in enumerate(channels, start=1)
    ]
    await message.answer("Список каналов:\n" + "\n".join(lines))
