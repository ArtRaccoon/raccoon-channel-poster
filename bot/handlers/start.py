from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards import main_menu_keyboard
from bot.states import BotStates

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return

    admin_ids: list[int] = message.bot["admin_ids"]
    if message.from_user.id not in admin_ids:
        await message.answer("Нет доступа.")
        return

    await state.set_state(BotStates.main_menu)
    await message.answer(
        "Добро пожаловать в Raccoon Channel Poster!",
        reply_markup=main_menu_keyboard(),
    )
