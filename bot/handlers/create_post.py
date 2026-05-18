from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from bot.keyboards import user_menu
from bot.services.channels import list_user_channels
from bot.services.posts import add_publish_log, create_draft, mark_published
from bot.states import CreatePostState

router = Router()


@router.message(F.text == '✍️ Создать пост')
async def create_post_start(message: Message, state: FSMContext):
    await state.set_state(CreatePostState.waiting_text)
    await message.answer('Отправьте текст поста.')


@router.message(CreatePostState.waiting_text)
async def receive_post_text(message: Message, state: FSMContext, config):
    if not message.text:
        await message.answer('Отправьте текст поста.')
        return

    channels = await list_user_channels(config.database_path, message.from_user.id)
    if not channels:
        await message.answer('Сначала добавьте хотя бы один канал.')
        await state.clear()
        return
    post_id = await create_draft(config.database_path, message.from_user.id, message.text)
    await state.update_data(post_id=post_id, text=message.text, channels=channels)
    await state.set_state(CreatePostState.waiting_channel)

    keys = [[KeyboardButton(text=f'{title or channel_id} | {channel_id}')] for channel_id, title, _, _ in channels]
    await message.answer(f'Предпросмотр:\n\n{message.text}\n\nВыберите канал:', reply_markup=ReplyKeyboardMarkup(keyboard=keys, resize_keyboard=True))


@router.message(CreatePostState.waiting_channel)
async def choose_channel(message: Message, state: FSMContext):
    data = await state.get_data()
    channels = data.get('channels', [])
    allowed_channel_ids = {str(channel_id) for channel_id, *_ in channels}

    if not message.text:
        await message.answer('Выберите канал из списка.')
        return

    channel_id = message.text.split('|')[-1].strip() if '|' in message.text else message.text.strip()
    if channel_id not in allowed_channel_ids:
        await message.answer('Выберите канал из списка.')
        return

    await state.update_data(channel_id=channel_id)
    await state.set_state(CreatePostState.waiting_action)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='✅ Опубликовать')],
            [KeyboardButton(text='💾 Оставить в черновиках')],
            [KeyboardButton(text='❌ Отменить')],
        ],
        resize_keyboard=True,
    )
    await message.answer('Выберите действие:', reply_markup=kb)


@router.message(CreatePostState.waiting_action)
async def handle_action(message: Message, state: FSMContext, bot, config):
    data = await state.get_data()
    channels = await list_user_channels(config.database_path, message.from_user.id)
    allowed_channel_ids = {str(channel_id) for channel_id, *_ in channels}
    is_owner = message.from_user.id in config.owner_ids

    if message.text == '💾 Оставить в черновиках':
        await message.answer('Сохранено в черновиках.', reply_markup=user_menu(is_owner))
    elif message.text == '❌ Отменить':
        await message.answer('Отменено.', reply_markup=user_menu(is_owner))
    elif message.text == '✅ Опубликовать':
        if data.get('channel_id') not in allowed_channel_ids:
            await message.answer('Выберите канал из списка.', reply_markup=user_menu(is_owner))
            await state.clear()
            return
        try:
            await bot.send_message(chat_id=data['channel_id'], text=data['text'])
            await mark_published(config.database_path, data['post_id'], data['channel_id'])
            await add_publish_log(config.database_path, message.from_user.id, data['channel_id'], data['post_id'], 'success')
            await message.answer('Пост опубликован.', reply_markup=user_menu(is_owner))
        except Exception as exc:
            await add_publish_log(config.database_path, message.from_user.id, data['channel_id'], data['post_id'], 'error', str(exc))
            await message.answer(f'Ошибка публикации: {exc}', reply_markup=user_menu(is_owner))
    else:
        await message.answer('Выберите действие кнопками.', reply_markup=user_menu(is_owner))
    await state.clear()
