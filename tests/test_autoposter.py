import asyncio
from bot.caption import LINKS_BLOCK, build_caption
from bot.config import Config
from bot.database import enqueue_media, init_db, queue_count, claim_next, recover_publishing, set_state, get_state
from bot.publisher import publish_next
from bot.proxy import build_session

def run(coro):
    return asyncio.run(coro)

def test_html_escaping_and_links():
    text = build_caption('<b>x</b> & y')
    assert '&lt;b&gt;x&lt;/b&gt; &amp; y' in text
    assert LINKS_BLOCK in text

def test_caption_limit_preserves_links():
    text = build_caption('x' * 5000)
    assert len(text) <= 1024
    assert text.endswith('Команда ArtRaccoon</a>')
    assert LINKS_BLOCK in text

def test_fifo_dedup_and_100_images(tmp_path):
    async def scenario():
        db = tmp_path/'bot.db'; await init_db(str(db))
        for i in range(100):
            assert await enqueue_media(str(db), 'photo', f'f{i}', None, i, i, 'g')
        assert not await enqueue_media(str(db), 'photo', 'f0', None, 0, 0, 'g')
        assert await queue_count(str(db)) == 100
        for i in range(100):
            item = await claim_next(str(db))
            assert item.file_id == f'f{i}'
    run(scenario())

def test_pause_resume_state(tmp_path):
    async def scenario():
        db = tmp_path/'bot.db'; await init_db(str(db))
        await set_state(str(db), 'paused', '1')
        assert await get_state(str(db), 'paused') == '1'
        await set_state(str(db), 'paused', '0')
        assert await get_state(str(db), 'paused') == '0'
    run(scenario())

class FakeBot:
    def __init__(self, fail=False): self.sent=[]; self.fail=fail
    async def send_photo(self, channel, file_id, **kwargs):
        if self.fail: raise OSError('network')
        self.sent.append(('photo', channel, file_id, kwargs))

def test_next_and_network_error_requeues(tmp_path):
    async def scenario():
        db = tmp_path/'bot.db'; await init_db(str(db))
        cfg = Config('token', '@ch', [1], 3, str(db), False, '', 30, False, 5, 'INFO')
        await enqueue_media(str(db), 'photo', 'file', 'cap', 1, 1, None)
        assert not await publish_next(FakeBot(fail=True), cfg)
        assert await queue_count(str(db)) == 1
        bot = FakeBot()
        assert await publish_next(bot, cfg)
        assert bot.sent[0][2] == 'file'
        assert await queue_count(str(db)) == 0
    run(scenario())

def test_recover_publishing(tmp_path):
    async def scenario():
        db = tmp_path/'bot.db'; await init_db(str(db))
        await enqueue_media(str(db), 'photo', 'file', None, 1, 1, None)
        await claim_next(str(db))
        assert await queue_count(str(db)) == 0
        await recover_publishing(str(db))
        assert await queue_count(str(db)) == 1
    run(scenario())

def test_proxy_session_enabled():
    cfg = Config('token', '@ch', [1], 3, 'data/bot.db', True, 'socks5h://127.0.0.1:1080', 30, True, 5, 'INFO')
    session = build_session(cfg)
    assert session.proxy == 'socks5://127.0.0.1:1080'
    assert session.raccoon_original_proxy_url == 'socks5h://127.0.0.1:1080'
