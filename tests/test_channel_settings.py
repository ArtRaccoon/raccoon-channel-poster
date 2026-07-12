import asyncio
from types import SimpleNamespace

from bot.database import Database
from bot.handlers import _bot_can_post, _channel_from_forward, _channel_from_username
from bot.models import ChannelSettings


def run(coro): return asyncio.run(coro)


def test_set_channel_via_forward_payload():
    msg = SimpleNamespace(forward_from_chat=SimpleNamespace(id=-1001, type='channel', title='ArtRaccoon', username='ArtRaccoon'))
    assert _channel_from_forward(msg) == ChannelSettings(-1001, 'ArtRaccoon', 'ArtRaccoon')


def test_set_channel_via_username_payload():
    class Bot:
        async def get_chat(self, username):
            assert username == '@ArtRaccoon'
            return SimpleNamespace(id=-1002, type='channel', title='ArtRaccoon', username='ArtRaccoon')
    assert run(_channel_from_username(Bot(), '@ArtRaccoon')) == ChannelSettings(-1002, 'ArtRaccoon', 'ArtRaccoon')


def test_bot_can_post_requires_admin_post_right():
    class Bot:
        async def get_me(self): return SimpleNamespace(id=42)
        async def get_chat_member(self, channel_id, user_id):
            assert (channel_id, user_id) == (-1001, 42)
            return SimpleNamespace(status='administrator', can_post_messages=True)
    assert run(_bot_can_post(Bot(), -1001)) is True


def test_replace_remove_and_restore_channel_after_restart(tmp_path):
    async def scenario():
        path = str(tmp_path/'autoposter.db')
        db = Database(path); await db.init()
        await db.set_channel(ChannelSettings(-1001, 'old', 'Old'))
        assert await db.get_channel() == ChannelSettings(-1001, 'old', 'Old')
        await db.set_channel(ChannelSettings(-1002, 'new', 'New'))
        assert await db.get_channel() == ChannelSettings(-1002, 'new', 'New')
        restarted = Database(path); await restarted.init()
        assert await restarted.get_channel() == ChannelSettings(-1002, 'new', 'New')
        await restarted.remove_channel()
        assert await restarted.get_channel() is None
    run(scenario())
