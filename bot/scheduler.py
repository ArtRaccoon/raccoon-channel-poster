from __future__ import annotations

import asyncio, logging
from datetime import datetime, timedelta, timezone
from aiogram import Bot
from .database import Database, utcnow
from .publisher import BACKOFFS, TemporaryPublishError, publish_next

log=logging.getLogger(__name__)

def parse_dt(value: str) -> datetime | None:
    if not value: return None
    try: return datetime.fromisoformat(value)
    except ValueError: return None

class Scheduler:
    def __init__(self, db:Database, bot:Bot, interval_hours:float):
        self.db=db; self.bot=bot; self.default_interval_hours=interval_hours; self._stop=asyncio.Event(); self._task=None
    async def current_interval(self) -> timedelta:
        interval_hours = await self.db.get_post_interval_hours(self.default_interval_hours)
        return timedelta(hours=interval_hours)

    async def ensure_next_run(self):
        if not await self.db.get_state("next_run_at"):
            await self.db.set_state("next_run_at", (datetime.now(timezone.utc)+await self.current_interval()).isoformat())
    async def start(self):
        await self.ensure_next_run(); self._task=asyncio.create_task(self.run())
    async def stop(self):
        self._stop.set()
        if self._task: await self._task
    async def run(self):
        backoff_index=0
        while not self._stop.is_set():
            try:
                if await self.db.paused():
                    await asyncio.wait_for(self._stop.wait(), 5); continue
                channel = await self.db.get_channel()
                if channel is None:
                    await asyncio.wait_for(self._stop.wait(), 1); continue
                due=parse_dt(await self.db.get_state("next_run_at")) or datetime.now(timezone.utc)
                wait=max(0,(due-datetime.now(timezone.utc)).total_seconds())
                if wait: await asyncio.wait_for(self._stop.wait(), min(wait,60)); continue
                try:
                    await publish_next(self.db, self.bot, channel.channel_id)
                    backoff_index=0
                    await self.db.set_state("next_run_at", (datetime.now(timezone.utc)+await self.current_interval()).isoformat())
                except TemporaryPublishError as exc:
                    delay=max(exc.delay or 0, BACKOFFS[min(backoff_index, len(BACKOFFS)-1)])
                    backoff_index+=1; log.warning("Temporary publish error; retry in %ss: %s", delay, exc)
                    await self.db.set_state("next_run_at", (datetime.now(timezone.utc)+timedelta(seconds=delay)).isoformat())
            except asyncio.TimeoutError:
                pass
