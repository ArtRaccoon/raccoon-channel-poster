from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.types import Update

from bot.config import load_settings
from bot.handlers import get_routers
from bot.proxy import create_http_session
from bot.storage import JsonStorage


def setup_logging(level: str) -> None:
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(logs_dir / "bot.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


async def run_bot() -> None:
    settings = load_settings()
    setup_logging(settings.log_level)
    logger = logging.getLogger(__name__)

    storage = JsonStorage(settings.data_dir)
    storage.ensure_files()
    settings.media_dir.mkdir(parents=True, exist_ok=True)

    session = create_http_session(settings.proxy_url)
    bot = Bot(token=settings.bot_token, session=session)
    bot["admin_ids"] = settings.admin_ids
    bot["proxy_url"] = settings.proxy_url
    bot["storage"] = storage

    dp = Dispatcher()

    @dp.update()
    async def admin_guard(update: Update) -> None:
        message = update.message
        if not message or not message.from_user:
            return
        if message.from_user.id not in settings.admin_ids:
            await message.answer("Нет доступа.")

    for router in get_routers():
        dp.include_router(router)

    logger.info("Bot started")
    try:
        await dp.start_polling(bot)
    except Exception:
        logger.exception("Bot crashed")
        raise
    finally:
        logger.info("Bot stopped")
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(run_bot())
