import asyncio
from bot.database import Database

def make_db(tmp_path):
    async def _make():
        d=Database(str(tmp_path/'autoposter.db')); await d.init(); return d
    return asyncio.run(_make())

def run(coro): return asyncio.run(coro)

def test_fifo_dedup_same_file_id_and_100_items(tmp_path):
    async def scenario():
        db=Database(str(tmp_path/'autoposter.db')); await db.init()
        assert await db.add_item(1,2,None,'photo','same','c') is True
        assert await db.add_item(1,2,None,'photo','same','c') is False
        assert await db.add_item(1,3,None,'photo','same','c') is True
        items=[(1,i,None,'photo',f'f{i}',None) for i in range(100,200)]
        assert await db.add_many(items) == 100
        first=await db.claim_next()
        assert first.source_message_id == 2
        assert await db.count_queued() == 101
    run(scenario())

def test_restore_publishing_pause_resume_skip_clear(tmp_path):
    async def scenario():
        db=Database(str(tmp_path/'autoposter.db')); await db.init()
        await db.add_item(1,1,None,'photo','f',None)
        item=await db.claim_next(); assert item.status == 'publishing'
        assert await db.restore_publishing() == 1
        assert await db.count_queued() == 1
        await db.set_paused(True); assert await db.paused() is True
        await db.set_paused(False); assert await db.paused() is False
        assert await db.skip_next() is True
        await db.add_item(1,2,None,'photo','f',None); await db.add_item(1,3,None,'photo','f',None)
        assert await db.clear_pending() == 2
    run(scenario())

def test_media_group_order_by_message_id(tmp_path):
    async def scenario():
        db=Database(str(tmp_path/'autoposter.db')); await db.init()
        await db.add_many([(1,12,'g','photo','b',None),(1,11,'g','photo','a','cap')])
        assert (await db.claim_next()).source_message_id == 11
    run(scenario())
