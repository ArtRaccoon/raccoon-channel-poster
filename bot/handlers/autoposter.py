from __future__ import annotations
import asyncio
from aiogram import F, Router, Bot
from aiogram.filters import Command
from aiogram.types import Message
from bot.config import Config
from bot.database import clear_queue, enqueue_media, get_state, queue_count, set_state, skip_next
from bot.publisher import next_time, publish_next

router = Router()
_batches: dict[int, tuple[int, asyncio.Task]] = {}

def is_admin(message: Message, config: Config) -> bool:
    return bool(message.from_user and message.from_user.id in config.admin_ids)

async def deny(message: Message) -> None:
    await message.answer('Нет доступа.')

async def batch_notify(message: Message, config: Config, added: int) -> None:
    if not config.batch_notification_enabled: return
    uid = message.from_user.id
    old = _batches.get(uid)
    total = added + (old[0] if old else 0)
    if old: old[1].cancel()
    async def later():
        try:
            await asyncio.sleep(config.batch_notification_delay_seconds)
            await message.answer(f'✅ Добавлено: {total}\n\n📚 В очереди: {await queue_count(config.database_path)}')
        except asyncio.CancelledError:
            pass
        finally:
            _batches.pop(uid, None)
    _batches[uid] = (total, asyncio.create_task(later()))

def extract_media(message: Message):
    if message.photo:
        return 'photo', message.photo[-1].file_id
    if message.video:
        return 'video', message.video.file_id
    if message.animation:
        return 'animation', message.animation.file_id
    if message.document and (message.document.mime_type or '').startswith('image/'):
        return 'document', message.document.file_id
    return None

@router.message(Command('start'))
async def start(message: Message, config: Config):
    if not is_admin(message, config): return await deny(message)
    await message.answer('Автопостер запущен. Отправляйте photo/video/GIF/images-as-document — они молча попадут в очередь.')

@router.message(Command('help'))
async def help_cmd(message: Message, config: Config):
    if not is_admin(message, config): return await deny(message)
    await message.answer('/status /queue /pause /resume /next /skip /clear confirm /help')

@router.message(Command('status'))
async def status(message: Message, config: Config):
    if not is_admin(message, config): return await deny(message)
    paused = await get_state(config.database_path, 'paused', '0') == '1'
    await message.answer(f'Публикация: {"пауза" if paused else "работает"}\nОчередь: {await queue_count(config.database_path)}\nСледующий запуск: {await get_state(config.database_path,"next_run_at","не запланирован")}\nПоследний успешный пост: {await get_state(config.database_path,"last_success_at","нет")}')

@router.message(Command('queue'))
async def queue(message: Message, config: Config):
    if not is_admin(message, config): return await deny(message)
    count = await queue_count(config.database_path); days = count * config.post_interval_hours / 24
    await message.answer(f'В очереди: {count}\nХватит примерно на: {days:.1f} дн.')

@router.message(Command('pause'))
async def pause(message: Message, config: Config):
    if not is_admin(message, config): return await deny(message)
    await set_state(config.database_path, 'paused', '1'); await message.answer('Публикация приостановлена.')

@router.message(Command('resume'))
async def resume(message: Message, config: Config):
    if not is_admin(message, config): return await deny(message)
    await set_state(config.database_path, 'paused', '0'); await message.answer('Публикация возобновлена.')

@router.message(Command('next'))
async def next_cmd(message: Message, bot: Bot, config: Config):
    if not is_admin(message, config): return await deny(message)
    ok = await publish_next(bot, config)
    await set_state(config.database_path, 'next_run_at', next_time(config.post_interval_seconds))
    await message.answer('Опубликовано.' if ok else 'Публиковать нечего или публикация на паузе.')

@router.message(Command('skip'))
async def skip(message: Message, config: Config):
    if not is_admin(message, config): return await deny(message)
    await message.answer('Пропущено.' if await skip_next(config.database_path) else 'Очередь пуста.')

@router.message(Command('clear'))
async def clear(message: Message, config: Config):
    if not is_admin(message, config): return await deny(message)
    if (message.text or '').strip() != '/clear confirm':
        return await message.answer('Для очистки используйте: /clear confirm')
    await message.answer(f'Очищено: {await clear_queue(config.database_path)}')

@router.message(F.content_type.in_({'photo','video','animation','document'}))
async def media(message: Message, config: Config):
    if not is_admin(message, config): return await deny(message)
    found = extract_media(message)
    if not found: return
    added = await enqueue_media(config.database_path, found[0], found[1], message.caption, message.message_id, None, message.media_group_id)
    if added: await batch_notify(message, config, 1)
