import asyncio
import pytest
from aiogram.exceptions import TelegramAPIError, TelegramNetworkError
from bot.database import Database
from bot.publisher import TemporaryPublishError, publish_next

class FakeBot:
    def __init__(self, fail=False): self.sent=[]; self.fail=fail
    async def send_photo(self, **kwargs):
        if self.fail: raise TelegramNetworkError(method='sendPhoto', message='down')
        self.sent.append(('photo', kwargs))
    async def send_video(self, **kwargs): self.sent.append(('video', kwargs))
    async def send_animation(self, **kwargs): self.sent.append(('animation', kwargs))
    async def send_document(self, **kwargs): self.sent.append(('document', kwargs))

class ApiFailBot(FakeBot):
    async def send_photo(self, **kwargs):
        raise TelegramAPIError(method='sendPhoto', message='telegram api error')

def run(coro): return asyncio.run(coro)

async def make_db(tmp_path):
    d=Database(str(tmp_path/'autoposter.db')); await d.init(); return d

def test_publish_next_and_next_while_paused(tmp_path):
    async def scenario():
        db=await make_db(tmp_path)
        await db.set_paused(True)
        await db.add_item(1,1,None,'photo','file','cap')
        bot=FakeBot()
        assert await publish_next(db, bot, '@c') is True
        assert await db.paused() is True
        assert len(bot.sent) == 1
    run(scenario())

def test_publish_supports_all_media_types(tmp_path):
    async def scenario():
        db=await make_db(tmp_path)
        for idx, media_type in enumerate(('photo', 'video', 'animation', 'document'), start=1):
            await db.add_item(1, idx, None, media_type, f'file-{idx}', None)
        bot=FakeBot()
        for _ in range(4):
            assert await publish_next(db, bot, -1001) is True
        assert [kind for kind, _ in bot.sent] == ['photo', 'video', 'animation', 'document']
    run(scenario())

def test_temporary_error_retries_current_and_no_overtake(tmp_path):
    async def scenario():
        db=await make_db(tmp_path)
        await db.add_item(1,1,None,'photo','first',None); await db.add_item(1,2,None,'photo','second',None)
        with pytest.raises(TemporaryPublishError): await publish_next(db, FakeBot(fail=True), '@c')
        bot=FakeBot(); await publish_next(db, bot, '@c')
        assert bot.sent[0][1]['photo'] == 'first'
    run(scenario())

def test_telegram_api_error_returns_item_to_queue(tmp_path):
    async def scenario():
        db=await make_db(tmp_path)
        await db.add_item(1, 1, None, 'photo', 'first', None)
        with pytest.raises(TemporaryPublishError):
            await publish_next(db, ApiFailBot(), '@c')
        assert await db.count_queued() == 1
        bot = FakeBot()
        await publish_next(db, bot, '@c')
        assert bot.sent[0][1]['photo'] == 'first'
    run(scenario())
