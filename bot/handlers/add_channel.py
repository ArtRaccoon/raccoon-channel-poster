from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards import user_menu
from bot.services.channels import add_channel
from bot.states import AddChannelState

router = Router()


@router.message(F.text == '➕ Добавить канал')
async def start_add_channel(message: Message, state: FSMContext):
    await state.set_state(AddChannelState.waiting_channel_ref)
    await message.answer(
        '1. Добавьте этого бота в ваш канал.\n'
        '2. Выдайте ему права администратора.\n'
        '3. Разрешите публиковать сообщения.\n'
        '4. Отправьте username канала, например @my_channel.'
    )


@router.message(AddChannelState.waiting_channel_ref)
async def handle_channel_ref(message: Message, state: FSMContext, bot, config):
    if not message.text:
        await message.answer('Отправьте username канала текстом, например @my_channel.')
        return

    channel_ref = message.text.strip()
    try:
        chat = await bot.get_chat(channel_ref)
    except Exception:
        await message.answer('Канал не найден или бот не добавлен в канал.')
        return

    try:
        bot_member = await bot.get_chat_member(chat.id, bot.id)
    except Exception:
        await message.answer('Не удалось проверить права бота в канале.')
        return

    if bot_member.status not in ('administrator', 'creator'):
        await message.answer('Бот не администратор в этом канале.')
        return

    can_edit = getattr(bot_member, 'can_edit_messages', False) is True or bot_member.status == 'creator'
    if not can_edit:
        await message.answer('Бот добавлен, но не может редактировать посты. Выдайте право редактирования сообщений.')
        return

    try:
        user_member = await bot.get_chat_member(chat.id, message.from_user.id)
    except Exception:
        await message.answer('Не удалось проверить права пользователя в канале.')
        return

    if user_member.status not in ('administrator', 'creator'):
        await message.answer('Пользователь не администратор канала.')
        return

    await add_channel(config.database_path, message.from_user.id, str(chat.id), chat.title, chat.username)
    await state.clear()
    is_owner = message.from_user.id in config.owner_ids
    await message.answer('Канал добавлен.', reply_markup=user_menu(is_owner))
