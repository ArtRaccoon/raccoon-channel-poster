import asyncio
import logging
import os
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher

from bot.config import load_config
from bot.database import init_db
from bot.handlers import add_channel, admin, create_post, help, my_channels, start, user_menu
from bot.proxy import build_session


def setup_logging(level_name: str) -> None:
    os.makedirs('logs', exist_ok=True)
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/bot.log', encoding='utf-8'),
        ],
    )


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

    await dp.start_polling(bot, config=config)


if __name__ == '__main__':
    asyncio.run(main())
