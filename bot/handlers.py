from __future__ import annotations

import asyncio, logging
from datetime import datetime
from zoneinfo import ZoneInfo
from collections.abc import Collection

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from .database import Database
from .models import ChannelSettings
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

SETCHANNEL_STATE = "awaiting_setchannel_admin_id"

def _channel_from_forward(message: Message) -> ChannelSettings | None:
    chat = getattr(message, "forward_from_chat", None)
    if chat is None:
        origin = getattr(message, "forward_origin", None)
        chat = getattr(origin, "chat", None)
    if chat is None or getattr(chat, "type", None) != "channel":
        return None
    return ChannelSettings(channel_id=chat.id, channel_username=getattr(chat, "username", None), channel_title=getattr(chat, "title", None))

async def _channel_from_username(bot: Bot, text: str) -> ChannelSettings | None:
    username = text.strip()
    if not username.startswith("@") or len(username) < 2 or any(ch.isspace() for ch in username):
        return None
    chat = await bot.get_chat(username)
    if getattr(chat, "type", None) != "channel":
        return None
    return ChannelSettings(channel_id=chat.id, channel_username=getattr(chat, "username", None), channel_title=getattr(chat, "title", None))

async def _bot_can_post(bot: Bot, channel_id: int) -> bool:
    me = await bot.get_me()
    member = await bot.get_chat_member(channel_id, me.id)
    return getattr(member, "status", None) == "administrator" and bool(getattr(member, "can_post_messages", False))

def _format_channel(channel: ChannelSettings, interval_hours: float | None = None, queued: int | None = None) -> str:
    username = f"@{channel.channel_username}" if channel.channel_username and not channel.channel_username.startswith("@") else (channel.channel_username or "—")
    lines = ["Название:", channel.channel_title or "—", "", "Username:", username, "", "ID:", str(channel.channel_id)]
    if interval_hours is not None:
        lines += ["", "Интервал публикации:", f"{interval_hours:g} ч."]
    if queued is not None:
        lines += ["", "Размер очереди:", str(queued)]
    return "\n".join(lines)

def create_router(db:Database, bot:Bot, interval_hours:float, timezone_name:str, notifier:BatchNotifier, admin_ids: Collection[int]) -> Router:
    router=Router()
    async def auth(message:Message) -> bool:
        if message.from_user and message.from_user.id in admin_ids: return True
        await message.answer("Нет доступа."); return False

    @router.message(Command("start"))
    async def start(message:Message):
        if not await auth(message): return
        if not await db.get_channel():
            await message.answer("Канал пока не настроен.\n\nДобавьте меня администратором канала.\n\nПосле этого:\n\n• перешлите любое сообщение из канала\n\nили\n\n• отправьте @username канала.")
            return
        await message.answer("Отправляйте медиа — оно автоматически добавляется в очередь. Публикация идёт каждые 3 часа.")

    @router.message(Command("help"))
    async def help_cmd(message:Message):
        if not await auth(message): return
        await message.answer("/start /help /status /channel /setchannel /removechannel /queue /pause /resume /next /skip /clear confirm")

    @router.message(Command("setchannel"))
    async def setchannel(message:Message):
        if not await auth(message): return
        await db.set_state(SETCHANNEL_STATE, str(message.from_user.id))
        await message.answer("Перешлите любое сообщение из канала или отправьте @username канала.")

    @router.message(Command("channel"))
    async def channel(message:Message):
        if not await auth(message): return
        channel_settings = await db.get_channel()
        if not channel_settings:
            await message.answer("Канал пока не настроен.")
            return
        await message.answer(_format_channel(channel_settings, interval_hours, await db.count_queued()))

    @router.message(Command("removechannel"))
    async def removechannel(message:Message):
        if not await auth(message): return
        await db.remove_channel()
        await db.set_state(SETCHANNEL_STATE, "")
        await message.answer("Канал удалён. Очередь сохранена.")

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
        channel_settings = await db.get_channel()
        if not channel_settings:
            await message.answer("Канал пока не настроен.")
            return
        try:
            ok=await publish_next(db, bot, channel_settings.channel_id)
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
        awaiting = await db.get_state(SETCHANNEL_STATE)
        channel_settings = _channel_from_forward(message)
        if awaiting == str(message.from_user.id) or channel_settings or (message.text or "").strip().startswith("@"):
            if channel_settings is None:
                try:
                    channel_settings = await _channel_from_username(bot, message.text or "")
                except Exception as exc:
                    log.warning("Failed to resolve channel username: %s", exc)
                    await message.answer("Не удалось получить канал. Проверьте @username и права доступа."); return
            if channel_settings is None:
                await message.answer("Перешлите сообщение из канала или отправьте @username канала."); return
            if not await _bot_can_post(bot, channel_settings.channel_id):
                await message.answer("❌\n\nДобавьте меня администратором\nс правом публикации сообщений."); return
            await db.set_channel(channel_settings)
            await db.set_state(SETCHANNEL_STATE, "")
            await message.answer("✅ Канал успешно подключён.\n\n" + _format_channel(channel_settings))
            return
        payload=media_payload(message)
        if not payload:
            await message.answer("Неподдерживаемый тип файла."); return
        media_type, file_id=payload
        added=await db.add_item(message.chat.id, message.message_id, message.media_group_id, media_type, file_id, message.caption)
        await notifier.added(message, 1 if added else 0)
    return router
