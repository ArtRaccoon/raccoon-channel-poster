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
from bot.handlers import add_channel, admin, batch_schedule, create_post, help, my_channels, settings, start, user_menu
from bot.proxy import build_session
from bot.services.posts import get_due_scheduled_posts


logger = logging.getLogger(__name__)


def setup_logging(level_name: str) -> None:
    os.makedirs('logs', exist_ok=True)
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s', handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler('logs/bot.log', encoding='utf-8')])


async def process_scheduled_posts(bot: Bot, db_path: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    posts = await get_due_scheduled_posts(db_path, now)
    from bot.services.publishing import publish_post
    for (post_id,) in posts:
        ok, msg = await publish_post(bot, db_path, post_id)
        if not ok:
            logger.error('Scheduled publish error for post_id=%s: %s', post_id, msg)


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
    dp.include_router(batch_schedule.router)
    dp.include_router(settings.router)
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
