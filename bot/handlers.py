from __future__ import annotations

import asyncio, logging
from datetime import datetime
from zoneinfo import ZoneInfo
from collections.abc import Collection

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from .database import Database
from .publisher import TemporaryPublishError, publish_next

log=logging.getLogger(__name__)

def is_image_document(message: Message) -> bool:
    return bool(message.document and (message.document.mime_type or "").startswith("image/"))

def media_payload(message: Message) -> tuple[str,str]|None:
    if message.photo: return "photo", message.photo[-1].file_id
    if message.video: return "video", message.video.file_id
    if message.animation: return "animation", message.animation.file_id
    if is_image_document(message): return "document", message.document.file_id
    return None

class BatchNotifier:
    def __init__(self, db:Database, enabled:bool, delay:float):
        self.db=db; self.enabled=enabled; self.delay=delay; self._counts={}; self._tasks={}
    async def added(self, message:Message, count:int):
        if not self.enabled or count<=0: return
        chat_id=message.chat.id; self._counts[chat_id]=self._counts.get(chat_id,0)+count
        if chat_id not in self._tasks or self._tasks[chat_id].done():
            self._tasks[chat_id]=asyncio.create_task(self._send_later(message))
    async def _send_later(self, message:Message):
        await asyncio.sleep(self.delay)
        chat_id=message.chat.id; added=self._counts.pop(chat_id,0); self._tasks.pop(chat_id,None)
        total=await self.db.count_queued()
        log.info("Batch added: %s; queued: %s", added, total)
        await message.answer(f"✅ Добавлено: {added}\n📚 В очереди: {total}")

def format_time(value:str, tzname:str) -> str:
    if not value: return "—"
    try: return datetime.fromisoformat(value).astimezone(ZoneInfo(tzname)).strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception: return value

def create_router(db:Database, bot:Bot, channel_id:str|int, interval_hours:float, timezone_name:str, notifier:BatchNotifier, admin_ids: Collection[int]) -> Router:
    router=Router()
    async def auth(message:Message) -> bool:
        if message.from_user and message.from_user.id in admin_ids: return True
        await message.answer("Нет доступа."); return False

    @router.message(Command("start"))
    async def start(message:Message):
        if not await auth(message): return
        await message.answer("Отправляйте медиа — оно автоматически добавляется в очередь. Публикация идёт каждые 3 часа.")

    @router.message(Command("help"))
    async def help_cmd(message:Message):
        if not await auth(message): return
        await message.answer("/start /help /status /queue /pause /resume /next /skip /clear confirm")

    @router.message(Command("status"))
    async def status(message:Message):
        if not await auth(message): return
        paused=await db.paused(); q=await db.count_queued()
        await message.answer(f"Автопубликация: {'пауза' if paused else 'включена'}\nОчередь: {q}\nСледующая публикация: {format_time(await db.get_state('next_run_at'), timezone_name)}\nПоследняя успешная: {format_time(await db.get_state('last_success_at'), timezone_name)}\nПоследняя ошибка: {await db.get_state('last_error') or '—'}")

    @router.message(Command("queue"))
    async def queue(message:Message):
        if not await auth(message): return
        q=await db.count_queued(); days=q*interval_hours/24
        await message.answer(f"В очереди: {q}\nХватит примерно на: {days:.1f} дн.")

    @router.message(Command("pause"))
    async def pause(message:Message):
        if not await auth(message): return
        await db.set_paused(True); log.info("Admin paused autoposting"); await message.answer("Автопубликация на паузе.")

    @router.message(Command("resume"))
    async def resume(message:Message):
        if not await auth(message): return
        await db.set_paused(False); log.info("Admin resumed autoposting"); await message.answer("Автопубликация возобновлена.")

    @router.message(Command("next"))
    async def next_cmd(message:Message):
        if not await auth(message): return
        was_paused=await db.paused()
        try:
            ok=await publish_next(db, bot, channel_id)
        except TemporaryPublishError as exc:
            await message.answer(f"Временная ошибка публикации: {exc}"); return
        if ok and not was_paused:
            from datetime import timedelta, timezone
            await db.set_state("next_run_at", (datetime.now(timezone.utc)+timedelta(hours=interval_hours)).isoformat())
        await message.answer("Опубликовано." if ok else "Очередь пуста.")

    @router.message(Command("skip"))
    async def skip(message:Message):
        if not await auth(message): return
        await message.answer("Первый элемент пропущен." if await db.skip_next() else "Очередь пуста.")

    @router.message(Command("clear"))
    async def clear(message:Message, command:CommandObject):
        if not await auth(message): return
        if (command.args or "").strip() != "confirm":
            await message.answer("Для очистки очереди отправьте: /clear confirm"); return
        count=await db.clear_pending(); await message.answer(f"Пропущено элементов: {count}")

    @router.message()
    async def media(message:Message):
        if not await auth(message): return
        payload=media_payload(message)
        if not payload:
            await message.answer("Неподдерживаемый тип файла."); return
        media_type, file_id=payload
        added=await db.add_item(message.chat.id, message.message_id, message.media_group_id, media_type, file_id, message.caption)
        await notifier.added(message, 1 if added else 0)
    return router
