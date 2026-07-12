import asyncio
from datetime import datetime, timedelta, timezone

from bot.database import Database
from bot.models import ChannelSettings
from bot.scheduler import Scheduler

class FakeBot:
    def __init__(self): self.sent=[]
    async def send_photo(self, **kwargs): self.sent.append(kwargs)

async def make_ready_db(tmp_path):
    db=Database(str(tmp_path/'autoposter.db')); await db.init()
    await db.set_state('next_run_at', (datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat())
    await db.add_item(1,1,None,'photo','file','cap')
    return db

def run(coro): return asyncio.run(coro)

def test_scheduler_does_not_publish_without_channel(tmp_path):
    async def scenario():
        db=await make_ready_db(tmp_path); bot=FakeBot(); scheduler=Scheduler(db, bot, 0.001)
        task=asyncio.create_task(scheduler.run())
        await asyncio.sleep(0.05); scheduler._stop.set(); await task
        assert bot.sent == []
        assert await db.count_queued() == 1
    run(scenario())

def test_scheduler_starts_after_channel_added(tmp_path):
    async def scenario():
        db=await make_ready_db(tmp_path); bot=FakeBot(); scheduler=Scheduler(db, bot, 0.001)
        task=asyncio.create_task(scheduler.run())
        await asyncio.sleep(0.01)
        await db.set_channel(ChannelSettings(-1001, 'art', 'Art'))
        await asyncio.sleep(1.1); scheduler._stop.set(); await task
        assert len(bot.sent) == 1
        assert bot.sent[0]['chat_id'] == -1001
    run(scenario())
