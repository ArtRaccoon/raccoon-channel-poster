from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards import main_menu_keyboard, settings_keyboard
from bot.states import BotStates

router = Router()


@router.message(lambda msg: msg.text == "Настройки")
async def open_settings(message: Message, state: FSMContext) -> None:
    await state.set_state(BotStates.settings_menu)
    await message.answer("Раздел настроек.", reply_markup=settings_keyboard())


@router.message(lambda msg: msg.text == "Прокси-статус")
async def proxy_status(message: Message) -> None:
    proxy_url: str = message.bot["proxy_url"]
    status = "включён" if proxy_url else "выключен"
    await message.answer(f"Прокси {status}.")


@router.message(lambda msg: msg.text == "Добавить канал")
async def add_channel_stub(message: Message) -> None:
    await message.answer("Добавление канала будет добавлено на следующем этапе.")


@router.message(lambda msg: msg.text == "Назад")
async def back_to_menu(message: Message, state: FSMContext) -> None:
    await state.set_state(BotStates.main_menu)
    await message.answer("Главное меню.", reply_markup=main_menu_keyboard())
