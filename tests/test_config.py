import os
import pytest
from bot.config import Config, ConfigError, parse_admin_ids, parse_channel_id
from bot.proxy import safe_proxy_url

def test_parse_admin_ids():
    assert parse_admin_ids('1, 2,3') == {1,2,3}

def test_env_loads_new_database(monkeypatch):
    monkeypatch.setenv('BOT_TOKEN','secret')
    monkeypatch.setenv('TARGET_CHANNEL_ID','-1001234567890')
    monkeypatch.setenv('ADMIN_IDS','1')
    cfg=Config.from_env(env_file=None)
    assert cfg.database_path == 'data/autoposter.db'
    assert cfg.target_channel_id == -1001234567890

def test_channel_username():
    assert parse_channel_id('@dummy') == '@dummy'

def test_required_missing(monkeypatch):
    for k in ['BOT_TOKEN','TARGET_CHANNEL_ID','ADMIN_IDS']:
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(ConfigError): Config.from_env(env_file=None)

def test_proxy_enabled_disabled(monkeypatch):
    monkeypatch.setenv('BOT_TOKEN','x'); monkeypatch.setenv('TARGET_CHANNEL_ID','@c'); monkeypatch.setenv('ADMIN_IDS','1')
    monkeypatch.setenv('PROXY_ENABLED','false')
    assert Config.from_env(env_file=None).proxy_enabled is False
    monkeypatch.setenv('PROXY_ENABLED','true'); monkeypatch.setenv('PROXY_URL','socks5h://user:pass@127.0.0.1:1080')
    cfg=Config.from_env(env_file=None)
    assert cfg.proxy_enabled is True
    assert safe_proxy_url(cfg.proxy_url) == 'socks5h://127.0.0.1:1080'
