from __future__ import annotations

import asyncio, logging, signal, sys
from pathlib import Path
from aiogram import Bot, Dispatcher
from .config import Config, ConfigError
from .database import Database
from .handlers import BatchNotifier, create_router
from .proxy import create_session, safe_proxy_url
from .scheduler import Scheduler

CONFIG: Config


def setup_logging(level:str) -> None:
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(level=getattr(logging, level, logging.INFO), format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("logs/bot.log")])

async def main() -> None:
    global CONFIG
    try:
        CONFIG = Config.from_env()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr); raise SystemExit(2) from exc
    setup_logging(CONFIG.log_level)
    log=logging.getLogger(__name__)
    log.info("Starting autoposter")
    if CONFIG.proxy_enabled: log.info("Telegram proxy enabled: %s", safe_proxy_url(CONFIG.proxy_url))
    else: log.info("Telegram proxy disabled")
    db=Database(CONFIG.database_path); await db.init(); restored=await db.restore_publishing()
    if restored: log.info("Restored publishing items: %s", restored)
    session=create_session(CONFIG.proxy_enabled, CONFIG.proxy_url, CONFIG.proxy_connect_timeout_seconds)
    bot=Bot(CONFIG.bot_token, session=session)
    dp=Dispatcher()
    notifier=BatchNotifier(db, CONFIG.batch_notification_enabled, CONFIG.batch_notification_delay_seconds)
    dp.include_router(create_router(db, bot, CONFIG.target_channel_id, CONFIG.post_interval_hours, CONFIG.timezone, notifier))
    scheduler=Scheduler(db, bot, CONFIG.target_channel_id, CONFIG.post_interval_hours)
    await scheduler.start()
    stop=asyncio.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try: asyncio.get_running_loop().add_signal_handler(sig, stop.set)
        except NotImplementedError: pass
    polling=asyncio.create_task(dp.start_polling(bot))
    waiter=asyncio.create_task(stop.wait())
    done, _=await asyncio.wait({polling, waiter}, return_when=asyncio.FIRST_COMPLETED)
    log.info("Stopping autoposter")
    polling.cancel(); await scheduler.stop(); await db.restore_publishing(); await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
