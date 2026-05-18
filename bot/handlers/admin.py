from aiogram import Router, F
from aiogram.types import Message

from bot.services.stats import get_admin_stats, latest_channels, latest_users

router = Router()


def _is_owner(message: Message, config) -> bool:
    return message.from_user.id in config.owner_ids


@router.message(F.text == '📊 Статистика')
async def admin_stats(message: Message, config):
    if not _is_owner(message, config):
        return
    s = await get_admin_stats(config.database_path)
    await message.answer(
        f"Всего пользователей: {s['total_users']}\n"
        f"Всего каналов: {s['total_channels']}\n"
        f"Всего постов: {s['total_posts']}\n"
        f"Опубликовано постов: {s['published_posts']}\n"
        f"Ошибок публикации: {s['publish_errors']}\n"
        f"Новых пользователей за 24ч: {s['new_users_24h']}"
    )


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


@router.message(F.text == '🌐 Прокси-статус')
async def admin_proxy_status(message: Message, config):
    if not _is_owner(message, config):
        return
    mode = 'proxy' if config.has_proxy else 'direct'
    await message.answer(f'PROXY_URL указан: {"да" if config.has_proxy else "нет"}\nРежим: {mode}')
