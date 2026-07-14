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


def test_interval_and_links_settings(tmp_path):
    async def scenario():
        db=Database(str(tmp_path/'autoposter.db')); await db.init()
        assert await db.get_post_interval_hours(3) == 3
        await db.set_post_interval_hours(2.5)
        assert await db.get_post_interval_hours(3) == 2.5
        assert await db.get_links_block('default') == 'default'
        await db.set_links_block('<b>links</b>')
        assert await db.get_links_block('default') == '<b>links</b>'
        await db.reset_links_block()
        assert await db.get_links_block('default') == 'default'
    run(scenario())
