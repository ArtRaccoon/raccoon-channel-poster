from __future__ import annotations
import asyncio, contextlib, logging, os, sys
from pathlib import Path
from aiogram import Bot, Dispatcher
from bot.config import load_config
from bot.database import init_db, recover_publishing
from bot.handlers import autoposter
from bot.proxy import build_session
from bot.publisher import AutoPoster

logger = logging.getLogger(__name__)

def setup_logging(level_name: str) -> None:
    os.makedirs('logs', exist_ok=True)
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s', handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler('logs/bot.log', encoding='utf-8')])

async def main() -> None:
    config = load_config(); setup_logging(config.log_level)
    if not config.bot_token: raise RuntimeError('BOT_TOKEN is not configured')
    if not config.target_channel_id: raise RuntimeError('TARGET_CHANNEL_ID is not configured')
    if not config.admin_ids: raise RuntimeError('ADMIN_IDS is not configured')
    Path(config.database_path).parent.mkdir(parents=True, exist_ok=True)
    await init_db(config.database_path); await recover_publishing(config.database_path)
    bot = Bot(token=config.bot_token, session=build_session(config))
    dp = Dispatcher(); dp.include_router(autoposter.router)
    poster = AutoPoster(bot, config); task = asyncio.create_task(poster.run())
    try:
        await dp.start_polling(bot, config=config, allowed_updates=['message'])
    finally:
        poster.stop(); task.cancel(); await bot.session.close()
        with contextlib.suppress(asyncio.CancelledError): await task

if __name__ == '__main__':
    asyncio.run(main())
