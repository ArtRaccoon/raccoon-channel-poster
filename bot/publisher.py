from __future__ import annotations

import asyncio
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter, TelegramAPIError
from .captions import DEFAULT_LINKS_BLOCK, build_caption
from .database import Database
from .models import QueueItem

BACKOFFS = [5, 15, 30, 60, 120, 300]
log = logging.getLogger(__name__)

class TemporaryPublishError(Exception):
    def __init__(self, message: str, delay: float | None = None):
        super().__init__(message); self.delay = delay

async def send_item(bot: Bot, channel_id: str|int, item: QueueItem, links_block: str = DEFAULT_LINKS_BLOCK) -> None:
    caption = build_caption(item.caption, links_block)
    kwargs = {"chat_id": channel_id, "caption": caption, "parse_mode": "HTML"}
    if item.media_type == "photo":
        await bot.send_photo(photo=item.file_id, **kwargs)
    elif item.media_type == "video":
        await bot.send_video(video=item.file_id, **kwargs)
    elif item.media_type == "animation":
        await bot.send_animation(animation=item.file_id, **kwargs)
    elif item.media_type == "document":
        await bot.send_document(document=item.file_id, **kwargs)
    else:
        raise ValueError(f"Unsupported media type: {item.media_type}")

async def publish_next(db: Database, bot: Bot, channel_id: str|int) -> bool:
    item = await db.claim_next()
    if not item:
        return False
    links_block = await db.get_links_block(DEFAULT_LINKS_BLOCK)
    try:
        await send_item(bot, channel_id, item, links_block)
    except TelegramRetryAfter as exc:
        await db.release_failed(item.id, f"Retry after {exc.retry_after}s")
        raise TemporaryPublishError("Telegram retry_after", float(exc.retry_after)) from exc
    except (TelegramNetworkError, TimeoutError, OSError, asyncio.TimeoutError) as exc:
        await db.release_failed(item.id, str(exc))
        raise TemporaryPublishError(str(exc)) from exc
    except TelegramAPIError as exc:
        await db.release_failed(item.id, str(exc))
        raise TemporaryPublishError(str(exc)) from exc
    await db.mark_published(item.id)
    await db.set_state("last_success_at", __import__('bot.database').database.utcnow())
    await db.set_state("last_error", "")
    log.info("Published queue item %s", item.id)
    return True
