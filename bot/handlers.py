from __future__ import annotations

import asyncio, logging
from datetime import datetime
from zoneinfo import ZoneInfo
from collections.abc import Collection

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from .database import Database
from .models import ChannelSettings
from .publisher import TemporaryPublishError, publish_next

log=logging.getLogger(__name__)

MAIN_MENU_BUTTONS = [
    ["📊 Статус", "📚 Очередь"],
    ["▶️ Опубликовать сейчас"],
    ["⏸ Пауза", "▶️ Продолжить"],
    ["⚙️ Канал", "🔗 Настроить канал"],
    ["🗑 Очистить очередь"],
    ["❓ Помощь"],
]

CLEAR_CONFIRM_BUTTONS = [
    ["✅ Да, очистить очередь"],
    ["❌ Отмена"],
]

def _reply_keyboard(rows: list[list[str]]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text) for text in row] for row in rows],
        resize_keyboard=True,
    )

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return _reply_keyboard(MAIN_MENU_BUTTONS)

def clear_confirm_keyboard() -> ReplyKeyboardMarkup:
    return _reply_keyboard(CLEAR_CONFIRM_BUTTONS)


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

    async def answer_with_menu(message: Message, text: str, **kwargs) -> None:
        await message.answer(text, reply_markup=main_menu_keyboard(), **kwargs)

    async def show_help(message: Message) -> None:
        await answer_with_menu(message, "/start /help /status /channel /setchannel /removechannel /queue /pause /resume /next /skip /clear confirm")

    async def show_status(message: Message) -> None:
        paused=await db.paused(); q=await db.count_queued()
        await answer_with_menu(message, f"Автопубликация: {'пауза' if paused else 'включена'}\nОчередь: {q}\nСледующая публикация: {format_time(await db.get_state('next_run_at'), timezone_name)}\nПоследняя успешная: {format_time(await db.get_state('last_success_at'), timezone_name)}\nПоследняя ошибка: {await db.get_state('last_error') or '—'}")

    async def show_queue(message: Message) -> None:
        q=await db.count_queued(); days=q*interval_hours/24
        await answer_with_menu(message, f"В очереди: {q}\nХватит примерно на: {days:.1f} дн.")

    async def pause_autoposting(message: Message) -> None:
        await db.set_paused(True); log.info("Admin paused autoposting"); await answer_with_menu(message, "Автопубликация на паузе.")

    async def resume_autoposting(message: Message) -> None:
        await db.set_paused(False); log.info("Admin resumed autoposting"); await answer_with_menu(message, "Автопубликация возобновлена.")

    async def show_channel(message: Message) -> None:
        channel_settings = await db.get_channel()
        if not channel_settings:
            await answer_with_menu(message, "Канал пока не настроен.")
            return
        await answer_with_menu(message, _format_channel(channel_settings, interval_hours, await db.count_queued()))

    async def start_setchannel(message: Message) -> None:
        await db.set_state(SETCHANNEL_STATE, str(message.from_user.id))
        await answer_with_menu(message, "Перешлите любое сообщение из канала или отправьте @username канала.")

    async def publish_next_now(message: Message) -> None:
        was_paused=await db.paused()
        channel_settings = await db.get_channel()
        if not channel_settings:
            await answer_with_menu(message, "Канал пока не настроен.")
            return
        try:
            ok=await publish_next(db, bot, channel_settings.channel_id)
        except TemporaryPublishError as exc:
            await answer_with_menu(message, f"Временная ошибка публикации: {exc}"); return
        if ok and not was_paused:
            from datetime import timedelta, timezone
            await db.set_state("next_run_at", (datetime.now(timezone.utc)+timedelta(hours=interval_hours)).isoformat())
        await answer_with_menu(message, "Опубликовано." if ok else "Очередь пуста.")

    async def ask_clear_confirmation(message: Message) -> None:
        await message.answer("Очистить очередь?", reply_markup=clear_confirm_keyboard())

    async def confirm_clear_queue(message: Message) -> None:
        count=await db.clear_pending(); await answer_with_menu(message, f"Очищено/пропущено элементов: {count}")

    async def cancel_clear_queue(message: Message) -> None:
        await answer_with_menu(message, "Очистка отменена")

    @router.message(Command("start"))
    async def start(message:Message):
        if not await auth(message): return
        if not await db.get_channel():
            await answer_with_menu(message, "Канал пока не настроен.\n\nДобавьте меня администратором канала.\n\nПосле этого:\n\n• перешлите любое сообщение из канала\n\nили\n\n• отправьте @username канала.")
            return
        await answer_with_menu(message, "Отправляйте медиа — оно автоматически добавляется в очередь. Публикация идёт каждые 3 часа.")

    @router.message(Command("help"))
    async def help_cmd(message:Message):
        if not await auth(message): return
        await show_help(message)

    @router.message(Command("setchannel"))
    async def setchannel(message:Message):
        if not await auth(message): return
        await start_setchannel(message)

    @router.message(Command("channel"))
    async def channel(message:Message):
        if not await auth(message): return
        await show_channel(message)

    @router.message(Command("removechannel"))
    async def removechannel(message:Message):
        if not await auth(message): return
        await db.remove_channel()
        await db.set_state(SETCHANNEL_STATE, "")
        await answer_with_menu(message, "Канал удалён. Очередь сохранена.")

    @router.message(Command("status"))
    async def status(message:Message):
        if not await auth(message): return
        await show_status(message)

    @router.message(Command("queue"))
    async def queue(message:Message):
        if not await auth(message): return
        await show_queue(message)

    @router.message(Command("pause"))
    async def pause(message:Message):
        if not await auth(message): return
        await pause_autoposting(message)

    @router.message(Command("resume"))
    async def resume(message:Message):
        if not await auth(message): return
        await resume_autoposting(message)

    @router.message(Command("next"))
    async def next_cmd(message:Message):
        if not await auth(message): return
        await publish_next_now(message)

    @router.message(Command("skip"))
    async def skip(message:Message):
        if not await auth(message): return
        await answer_with_menu(message, "Первый элемент пропущен." if await db.skip_next() else "Очередь пуста.")

    @router.message(Command("clear"))
    async def clear(message:Message, command:CommandObject):
        if not await auth(message): return
        if (command.args or "").strip() != "confirm":
            await ask_clear_confirmation(message); return
        await confirm_clear_queue(message)

    @router.message(F.text == "📊 Статус")
    async def status_button(message:Message):
        if not await auth(message): return
        await show_status(message)

    @router.message(F.text == "📚 Очередь")
    async def queue_button(message:Message):
        if not await auth(message): return
        await show_queue(message)

    @router.message(F.text == "▶️ Опубликовать сейчас")
    async def next_button(message:Message):
        if not await auth(message): return
        await publish_next_now(message)

    @router.message(F.text == "⏸ Пауза")
    async def pause_button(message:Message):
        if not await auth(message): return
        await pause_autoposting(message)

    @router.message(F.text == "▶️ Продолжить")
    async def resume_button(message:Message):
        if not await auth(message): return
        await resume_autoposting(message)

    @router.message(F.text == "⚙️ Канал")
    async def channel_button(message:Message):
        if not await auth(message): return
        await show_channel(message)

    @router.message(F.text == "🔗 Настроить канал")
    async def setchannel_button(message:Message):
        if not await auth(message): return
        await start_setchannel(message)

    @router.message(F.text == "🗑 Очистить очередь")
    async def clear_button(message:Message):
        if not await auth(message): return
        await ask_clear_confirmation(message)

    @router.message(F.text == "✅ Да, очистить очередь")
    async def clear_confirm_button(message:Message):
        if not await auth(message): return
        await confirm_clear_queue(message)

    @router.message(F.text == "❌ Отмена")
    async def clear_cancel_button(message:Message):
        if not await auth(message): return
        await cancel_clear_queue(message)

    @router.message(F.text == "❓ Помощь")
    async def help_button(message:Message):
        if not await auth(message): return
        await show_help(message)

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
            await answer_with_menu(message, "✅ Канал успешно подключён.\n\n" + _format_channel(channel_settings))
            return
        payload=media_payload(message)
        if not payload:
            await message.answer("Неподдерживаемый тип файла."); return
        media_type, file_id=payload
        added=await db.add_item(message.chat.id, message.message_id, message.media_group_id, media_type, file_id, message.caption)
        await notifier.added(message, 1 if added else 0)
    return router
