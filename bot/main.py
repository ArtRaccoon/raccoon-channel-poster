import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import load_config
from bot.database import init_db
from bot.handlers import add_channel, admin, create_post, help, my_channels, start, user_menu
from bot.proxy import build_session
from bot.services.channels import has_user_channel
from bot.services.posts import CAPTION_LIMIT, add_publish_log, get_due_scheduled_posts, set_post_status


logger = logging.getLogger(__name__)


def setup_logging(level_name: str) -> None:
    os.makedirs('logs', exist_ok=True)
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s', handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler('logs/bot.log', encoding='utf-8')])


async def process_scheduled_posts(bot: Bot, db_path: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    posts = await get_due_scheduled_posts(db_path, now)
    for post_id, owner_id, channel_id, text, media_file_id, media_type in posts:
        if not channel_id:
            await set_post_status(db_path, post_id, 'failed')
            await add_publish_log(db_path, owner_id, '', post_id, 'error', 'Scheduled post has no channel_id')
            continue
        if not await has_user_channel(db_path, owner_id, str(channel_id)):
            await set_post_status(db_path, post_id, 'failed')
            await add_publish_log(db_path, owner_id, str(channel_id), post_id, 'error', 'Channel is inactive or not owned by user')
            continue
        try:
            if media_type == 'photo':
                if text and len(text) > CAPTION_LIMIT:
                    raise ValueError('Подпись к фото не должна быть длиннее 1024 символов.')
                await bot.send_photo(chat_id=channel_id, photo=media_file_id, caption=text or None)
            else:
                await bot.send_message(chat_id=channel_id, text=text or '')
            await set_post_status(db_path, post_id, 'published')
            await add_publish_log(db_path, owner_id, channel_id, post_id, 'success')
        except Exception as exc:
            logger.exception('Scheduled publish error for post_id=%s', post_id)
            await set_post_status(db_path, post_id, 'failed')
            await add_publish_log(db_path, owner_id, channel_id or '', post_id, 'error', str(exc))


async def main() -> None:
    config = load_config()
    if not config.bot_token:
        raise RuntimeError('BOT_TOKEN is not configured')
    setup_logging(config.log_level)
    Path(config.database_path).parent.mkdir(parents=True, exist_ok=True)
    await init_db(config.database_path)

    session = build_session(config.proxy_url)
    bot = Bot(token=config.bot_token, session=session)
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(help.router)
    dp.include_router(user_menu.router)
    dp.include_router(add_channel.router)
    dp.include_router(my_channels.router)
    dp.include_router(create_post.router)
    dp.include_router(admin.router)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(process_scheduled_posts, 'interval', seconds=30, args=[bot, config.database_path])
    scheduler.start()
    try:
        await dp.start_polling(bot, config=config)
    finally:
        scheduler.shutdown(wait=False)


if __name__ == '__main__':
    asyncio.run(main())
