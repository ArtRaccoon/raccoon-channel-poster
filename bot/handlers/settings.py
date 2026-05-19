from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

router = Router()


@router.message(F.text == '⚙️ Настройки')
async def open_settings(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✍️ Автоподпись каналов', callback_data='stub')],
        [InlineKeyboardButton(text='🗓 Расписание каналов', callback_data='stub')],
        [InlineKeyboardButton(text='🔗 Кнопки каналов', callback_data='stub')],
    ])
    await message.answer('Настройки:', reply_markup=kb)
