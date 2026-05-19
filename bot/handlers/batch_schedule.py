import asyncio
import json
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.keyboards import post_actions_inline
from bot.services.batches import create_batch, get_batch, update_batch_status
from bot.services.channels import get_channel_settings, has_user_channel, list_user_channels, update_channel_field
from bot.services.posts import (
    create_draft_with_batch,
    delete_batch_posts,
    get_post,
    list_any_batch_posts,
    list_batch_posts,
    set_post_status,
)
from bot.services.schedules import clear_channel_schedule, get_channel_schedule, replace_channel_schedule
from bot.services.publishing import render_post_preview
from bot.states import CreatePostState

router = Router()
DAY_MAP = {'Пн': 0, 'Вт': 1, 'Ср': 2, 'Чт': 3, 'Пт': 4, 'Сб': 5, 'Вс': 6}
REV_DAY = {v: k for k, v in DAY_MAP.items()}
DEFAULT_TIMES = ['11:00', '14:00', '17:00', '20:00']
BATCH_ALBUM_BUFFER: dict[str, list[Message]] = {}
BATCH_ALBUM_TASKS: dict[str, asyncio.Task] = {}


def _default_slots():
    return [(d, t) for d in range(7) for t in DEFAULT_TIMES]


def _format_schedule(slots: list[tuple[int, str]]) -> str:
    grouped = {d: [] for d in range(7)}
    for d, t in sorted(slots):
        grouped[d].append(t)
    return '\n'.join(f"{REV_DAY[d]}: {', '.join(grouped[d])}" for d in range(7))


def _parse_schedule(text: str):
    result = []
    seen = set()
    for raw in [x.strip() for x in text.splitlines() if x.strip()]:
        if ':' not in raw:
            raise ValueError('Неверный формат строки расписания.')
        day, times = raw.split(':', 1)
        day = day.strip()
        if day not in DAY_MAP:
            raise ValueError('Используйте дни: Пн, Вт, Ср, Чт, Пт, Сб, Вс.')
        for tm in [t.strip() for t in times.split(',') if t.strip()]:
            if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', tm):
                raise ValueError(f'Неверное время: {tm}')
            key = (DAY_MAP[day], tm)
            if key not in seen:
                seen.add(key)
                result.append(key)
    if not result:
        raise ValueError('Расписание пустое.')
    return sorted(result)


async def _show_schedule_choice(message: Message, owner_id: int, channel_id: str, db_path: str):
    slots = await get_channel_schedule(db_path, owner_id, channel_id)
    if not slots:
        slots = _default_slots()
    text = 'Текущее расписание:\n\n' + _format_schedule(slots)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ Оставить это расписание', callback_data=f'batch_keep:{channel_id}')],
        [InlineKeyboardButton(text='✏️ Редактировать расписание', callback_data=f'batch_edit_sched:{channel_id}')],
        [InlineKeyboardButton(text='❌ Отменить', callback_data='batch_cancel')],
    ])
    await message.answer(text, reply_markup=kb)


@router.message(F.text == '🗓 Расписание')
async def batch_start(message: Message, state: FSMContext, config):
    channels = await list_user_channels(config.database_path, message.from_user.id, only_active=True)
    if not channels:
        await message.answer('Сначала добавьте хотя бы один активный канал.')
        return
    await state.set_state(CreatePostState.waiting_batch_channel)
    kb = [[InlineKeyboardButton(text=(title or channel_id), callback_data=f'batch_ch:{channel_id}')] for channel_id, title, *_ in channels]
    await message.answer('Выберите канал.', reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data.startswith('batch_ch:'))
async def batch_choose_channel(call: CallbackQuery, state: FSMContext, config):
    channel_id = call.data.split(':', 1)[1]
    if not await has_user_channel(config.database_path, call.from_user.id, channel_id):
        await call.answer('Канал недоступен', show_alert=True)
        return
    await state.update_data(batch_channel_id=channel_id)
    await call.answer()
    await _show_schedule_choice(call.message, call.from_user.id, channel_id, config.database_path)


@router.callback_query(F.data == 'batch_cancel')
async def batch_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer('Отменено.')
    await call.answer()


@router.callback_query(F.data.startswith('batch_edit_sched:'))
async def batch_edit_sched(call: CallbackQuery, state: FSMContext):
    channel_id = call.data.split(':', 1)[1]
    await state.set_state(CreatePostState.waiting_batch_schedule_text)
    await state.update_data(batch_channel_id=channel_id)
    await call.message.answer('Отправьте расписание в формате:\nПн: 11:00, 14:00\nВт: 12:00, 18:00')
    await call.answer()


async def _start_collecting(message: Message, state: FSMContext, config, channel_id: str):
    batch_id = await create_batch(config.database_path, message.from_user.id, channel_id, 'collecting')
    await state.set_state(CreatePostState.waiting_batch_content)
    await state.update_data(batch_id=batch_id, batch_count=0, batch_channel_id=channel_id)
    await message.answer('Отправляйте медиа для расписания. Одиночное фото = отдельный пост. Сгруппированные фото = один альбом. Когда закончите, отправьте: готово')


@router.callback_query(F.data.startswith('batch_keep:'))
async def batch_keep_sched(call: CallbackQuery, state: FSMContext, config):
    channel_id = call.data.split(':', 1)[1]
    if not await has_user_channel(config.database_path, call.from_user.id, channel_id):
        await call.answer('Канал недоступен', show_alert=True)
        return
    await _start_collecting(call.message, state, config, channel_id)
    await call.answer()


@router.message(CreatePostState.waiting_batch_schedule_text)
async def batch_apply_sched_text(message: Message, state: FSMContext, config):
    data = await state.get_data()
    channel_id = data.get('batch_channel_id')
    if not channel_id or not await has_user_channel(config.database_path, message.from_user.id, channel_id):
        await state.clear()
        return
    try:
        slots = _parse_schedule(message.text or '')
    except ValueError as e:
        await message.answer(str(e))
        return
    await replace_channel_schedule(config.database_path, message.from_user.id, channel_id, slots)
    await _start_collecting(message, state, config, channel_id)


async def _save_album_batch(group_id: str, state: FSMContext, config):
    await asyncio.sleep(1.7)
    items = BATCH_ALBUM_BUFFER.pop(group_id, [])
    BATCH_ALBUM_TASKS.pop(group_id, None)
    if not items:
        return
    msg = items[0]
    data = await state.get_data()
    batch_id = data.get('batch_id')
    channel_id = data.get('batch_channel_id')
    if not batch_id or not channel_id:
        return
    media = [{"file_id": m.photo[-1].file_id} for m in items if m.photo]
    if len(media) < 2:
        return
    caption = next((m.caption for m in items if m.caption), None)
    await create_draft_with_batch(config.database_path, msg.from_user.id, channel_id, batch_id, caption, None, 'album', json.dumps(media), group_id)
    count = int(data.get('batch_count', 0)) + 1
    await state.update_data(batch_count=count)
    await msg.answer(f'Добавлено: {count}')


@router.message(CreatePostState.waiting_batch_content)
async def batch_collect(message: Message, state: FSMContext, config):
    data = await state.get_data()
    batch_id = data.get('batch_id')
    channel_id = data.get('batch_channel_id')
    if not batch_id or not channel_id:
        await state.clear()
        return
    if (message.text or '').strip().lower() == 'готово':
        posts = await list_batch_posts(config.database_path, message.from_user.id, batch_id)
        if not posts:
            await message.answer('Пока нет постов для планирования.')
            return
        slots = await get_channel_schedule(config.database_path, message.from_user.id, channel_id)
        if not slots:
            slots = _default_slots()
            await replace_channel_schedule(config.database_path, message.from_user.id, channel_id, slots)
        tz = (await get_channel_settings(config.database_path, message.from_user.id, channel_id) or {}).get('channel_timezone') or config.timezone
        base = datetime.now(ZoneInfo(tz)).replace(second=0, microsecond=0)
        assigned = []
        for i, (post_id, _) in enumerate(posts):
            dt = _next_slot(base, slots, i)
            await set_post_status(config.database_path, post_id, 'scheduled', scheduled_at=dt.astimezone(ZoneInfo('UTC')).isoformat())
            assigned.append((post_id, dt))
        await update_batch_status(config.database_path, batch_id, message.from_user.id, 'scheduled')
        lines = [f'Запланировано постов: {len(assigned)}', '']
        for idx, (post_id, dt) in enumerate(assigned, start=1):
            lines.append(f'{idx}. #{post_id} — {REV_DAY[dt.weekday()]} {dt.strftime("%H:%M")}')
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='👁 Посмотреть расписание', callback_data=f'batch_view:{batch_id}')],
            [InlineKeyboardButton(text='✏️ Редактировать отдельные посты', callback_data=f'batch_posts:{batch_id}')],
            [InlineKeyboardButton(text='✅ Готово', callback_data='batch_done')],
            [InlineKeyboardButton(text='❌ Отменить расписание', callback_data=f'batch_drop:{batch_id}')],
        ])
        await state.set_state(CreatePostState.waiting_batch_review)
        await message.answer('\n'.join(lines), reply_markup=kb)
        return

    if message.media_group_id and message.photo:
        gid = message.media_group_id
        BATCH_ALBUM_BUFFER.setdefault(gid, []).append(message)
        if gid in BATCH_ALBUM_TASKS:
            BATCH_ALBUM_TASKS[gid].cancel()
        BATCH_ALBUM_TASKS[gid] = asyncio.create_task(_save_album_batch(gid, state, config))
        return

    media_type, media_file_id, text = 'text', None, message.text
    if message.photo:
        media_type, media_file_id, text = 'photo', message.photo[-1].file_id, message.caption
    if media_type == 'text' and not text:
        return
    await create_draft_with_batch(config.database_path, message.from_user.id, channel_id, batch_id, text, media_file_id, media_type)
    count = int(data.get('batch_count', 0)) + 1
    await state.update_data(batch_count=count)
    await message.answer(f'Добавлено: {count}')


def _next_slot(base: datetime, slots: list[tuple[int, str]], offset: int) -> datetime:
    candidates = []
    for d in range(0, 28):
        day = (base + timedelta(days=d)).date()
        wd = day.weekday()
        for swd, tm in slots:
            if swd != wd:
                continue
            hh, mm = map(int, tm.split(':'))
            dt = datetime(day.year, day.month, day.day, hh, mm, tzinfo=base.tzinfo)
            if dt >= base:
                candidates.append(dt)
    candidates.sort()
    return candidates[offset] if offset < len(candidates) else candidates[-1] + timedelta(hours=3 * (offset - len(candidates) + 1))


@router.callback_query(F.data == 'batch_done')
async def batch_done(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer('Готово.')
    await call.answer()


@router.callback_query(F.data.startswith('batch_drop:'))
async def batch_drop(call: CallbackQuery, config, state: FSMContext):
    batch_id = int(call.data.split(':', 1)[1])
    batch = await get_batch(config.database_path, batch_id, call.from_user.id)
    if not batch:
        await call.answer('Нет доступа', show_alert=True)
        return
    await delete_batch_posts(config.database_path, call.from_user.id, batch_id)
    await update_batch_status(config.database_path, batch_id, call.from_user.id, 'cancelled')
    await state.clear()
    await call.message.answer('Расписание отменено.')
    await call.answer()


@router.callback_query(F.data.startswith('batch_view:'))
async def batch_view(call: CallbackQuery, config):
    batch_id = int(call.data.split(':', 1)[1])
    rows = await list_any_batch_posts(config.database_path, call.from_user.id, batch_id)
    batch = await get_batch(config.database_path, batch_id, call.from_user.id)
    if not batch:
        await call.answer('Нет доступа', show_alert=True)
        return
    tz = (await get_channel_settings(config.database_path, call.from_user.id, batch[2]) or {}).get('channel_timezone') or config.timezone
    lines = ['Расписание batch:']
    for i, (pid, sat) in enumerate(rows, start=1):
        dt = datetime.fromisoformat(sat).astimezone(ZoneInfo(tz))
        lines.append(f'{i}. #{pid} — {REV_DAY[dt.weekday()]} {dt.strftime("%H:%M")}')
    await call.message.answer('\n'.join(lines))
    await call.answer()


@router.callback_query(F.data.startswith('batch_posts:'))
async def batch_posts(call: CallbackQuery, config):
    batch_id = int(call.data.split(':', 1)[1])
    rows = await list_any_batch_posts(config.database_path, call.from_user.id, batch_id)
    kb = []
    for pid, _ in rows:
        kb.append([InlineKeyboardButton(text=f'Пост #{pid}', callback_data=f'batch_post_open:{pid}')])
    await call.message.answer('Выберите пост:', reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await call.answer()


@router.callback_query(F.data.startswith('batch_post_open:'))
async def batch_post_open(call: CallbackQuery, config):
    post_id = int(call.data.split(':', 1)[1])
    post = await get_post(config.database_path, post_id)
    if not post or post[1] != call.from_user.id:
        await call.answer('Нет доступа', show_alert=True)
        return
    channel = await get_channel_settings(config.database_path, call.from_user.id, post[2]) if post[2] else None
    await render_post_preview(call.bot, call.from_user.id, post, channel)
    await call.message.answer('Пост загружен. Что сделать дальше?', reply_markup=post_actions_inline(post_id, bool(post[13]), include_time_change=True))
    await call.answer()
