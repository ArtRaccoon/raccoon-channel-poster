import sqlite3
from datetime import datetime
from pathlib import Path

from aiogram import F, Router
from aiogram.types import FSInputFile, Message

from bot.services.posts import latest_publish_errors
from bot.services.stats import get_admin_stats, latest_channels, latest_users

router = Router()


def _is_owner(message: Message, config) -> bool:
    return message.from_user.id in config.owner_ids


def _render_stats(s: dict) -> str:
    top_channels = '\n'.join([f"{uid}: {cnt}" for uid, cnt in s['top_channels']]) or '-'
    top_pubs = '\n'.join([f"{uid}: {cnt}" for uid, cnt in s['top_pubs']]) or '-'
    return (
        f"Всего пользователей: {s['total_users']}\nНовых за 24ч: {s['new_users_24h']}\nНовых за 7д: {s['new_users_7d']}\n"
        f"Всего каналов: {s['total_channels']}\nАктивных: {s['active_channels']}\nОтключённых: {s['disabled_channels']}\n"
        f"Всего постов: {s['total_posts']}\nЧерновики: {s['drafts']}\nЗапланированных: {s['scheduled']}\n"
        f"Опубликованных: {s['published']}\nОшибок публикации: {s['failed']}\n"
        f"Публикаций за 24ч: {s['published_24h']}\nПубликаций за 7д: {s['published_7d']}\n"
        f"Топ-5 по каналам:\n{top_channels}\nТоп-5 по публикациям:\n{top_pubs}"
    )


def _short(text: str | None, limit: int = 120) -> str:
    value = (text or '-').replace('\n', ' ')
    return value if len(value) <= limit else f'{value[:limit - 3]}...'


@router.message(F.text == '📊 Статистика')
@router.message(F.text == '📈 Отчёт за 24ч')
@router.message(F.text == '📈 Отчёт за 7д')
async def admin_stats(message: Message, config):
    if not _is_owner(message, config):
        return
    s = await get_admin_stats(config.database_path)
    await message.answer(_render_stats(s))


@router.message(F.text == '👥 Пользователи')
async def admin_users(message: Message, config):
    if not _is_owner(message, config):
        return
    rows = await latest_users(config.database_path)
    text = ['Последние 10 пользователей:']
    for tid, username, first_name, channels_count, posts_count in rows:
        text.append(f'{tid} | @{username or "-"} | {first_name or "-"} | каналов={channels_count} | постов={posts_count}')
    await message.answer('\n'.join(text))


@router.message(F.text == '📣 Каналы')
async def admin_channels(message: Message, config):
    if not _is_owner(message, config):
        return
    rows = await latest_channels(config.database_path)
    text = ['Последние 10 каналов:']
    for title, channel_id, owner_id, is_active in rows:
        text.append(f'{title or "-"} | {channel_id} | owner={owner_id} | is_active={is_active}')
    await message.answer('\n'.join(text))


@router.message(F.text == '💾 Бэкап базы')
async def admin_backup_db(message: Message, config):
    if not _is_owner(message, config):
        return
    source = Path(config.database_path)
    if not source.exists():
        await message.answer(f'База не найдена: {source}')
        return
    backup_dir = Path('backups')
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f'bot_backup_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.db'
    with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
        src.backup(dst)
    await message.answer(f'Бэкап создан: {target}')
    try:
        await message.answer_document(FSInputFile(target))
    except Exception as exc:
        await message.answer(f'Файл бэкапа создан, но не удалось отправить документ: {_short(str(exc))}')


@router.message(F.text == '🚨 Ошибки')
async def admin_publish_errors(message: Message, config):
    if not _is_owner(message, config):
        return
    rows = await latest_publish_errors(config.database_path)
    if not rows:
        await message.answer('Ошибок публикации пока нет.')
        return
    text = ['Последние 10 ошибок публикации:']
    for created_at, owner_id, channel_id, post_id, error in rows:
        text.append(f'{created_at} | owner={owner_id} | channel={channel_id or "-"} | post=#{post_id} | {_short(error)}')
    await message.answer('\n'.join(text))


@router.message(F.text == '🌐 Прокси-статус')
async def admin_proxy_status(message: Message, config):
    if not _is_owner(message, config):
        return
    mode = 'proxy' if config.has_proxy else 'direct'
    await message.answer(f'PROXY_URL указан: {"да" if config.has_proxy else "нет"}\nРежим: {mode}')
