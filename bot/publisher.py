from __future__ import annotations
import asyncio, logging
from datetime import datetime, timedelta, timezone
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramNetworkError, TelegramAPIError
from bot.caption import build_caption
from bot.config import Config
from bot.database import claim_next, get_state, mark_published, queue_count, requeue_failed, set_state, QueueItem

logger = logging.getLogger(__name__)
BACKOFFS = [5, 15, 30, 60, 120, 300]

def parse_channel(raw: str):
    return int(raw) if raw.lstrip('-').isdigit() else raw

def next_time(interval_seconds: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=interval_seconds)).isoformat()

async def publish_item(bot: Bot, channel_id, item: QueueItem) -> None:
    caption = build_caption(item.caption)
    kwargs = {'caption': caption, 'parse_mode': 'HTML'}
    if item.media_type == 'photo':
        await bot.send_photo(channel_id, item.file_id, **kwargs)
    elif item.media_type == 'video':
        await bot.send_video(channel_id, item.file_id, **kwargs)
    elif item.media_type == 'animation':
        await bot.send_animation(channel_id, item.file_id, **kwargs)
    elif item.media_type == 'document':
        await bot.send_document(channel_id, item.file_id, **kwargs)
    else:
        raise ValueError(f'Unsupported media type: {item.media_type}')

async def publish_next(bot: Bot, config: Config) -> bool:
    if await get_state(config.database_path, 'paused', '0') == '1':
        return False
    item = await claim_next(config.database_path)
    if not item:
        return False
    try:
        await publish_item(bot, parse_channel(config.target_channel_id), item)
    except TelegramRetryAfter as e:
        await requeue_failed(config.database_path, item.id, f'retry_after:{e.retry_after}')
        logger.warning('Telegram retry-after: %s', e.retry_after)
        return False
    except (TelegramNetworkError, TelegramAPIError, TimeoutError, OSError, asyncio.TimeoutError) as e:
        await requeue_failed(config.database_path, item.id, type(e).__name__)
        logger.exception('Publication failed; item returned to queue')
        return False
    await mark_published(config.database_path, item.id)
    return True

class AutoPoster:
    def __init__(self, bot: Bot, config: Config):
        self.bot = bot; self.config = config; self._stop = asyncio.Event()
    def stop(self) -> None: self._stop.set()
    async def run(self) -> None:
        backoff_idx = 0
        while not self._stop.is_set():
            try:
                if await queue_count(self.config.database_path) and await get_state(self.config.database_path, 'paused', '0') != '1':
                    await publish_next(self.bot, self.config)
                await set_state(self.config.database_path, 'next_run_at', next_time(self.config.post_interval_seconds))
                backoff_idx = 0
                await asyncio.wait_for(self._stop.wait(), timeout=self.config.post_interval_seconds)
            except asyncio.TimeoutError:
                continue
            except Exception:
                delay = BACKOFFS[min(backoff_idx, len(BACKOFFS)-1)]
                backoff_idx += 1
                logger.exception('Scheduler error; retrying in %s seconds', delay)
                try: await asyncio.wait_for(self._stop.wait(), timeout=delay)
                except asyncio.TimeoutError: pass
