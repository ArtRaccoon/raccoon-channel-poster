from __future__ import annotations
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import ClientTimeout
from bot.config import Config

SUPPORTED_PROXY_SCHEMES = ('socks5://', 'socks5h://')

def build_session(config: Config) -> AiohttpSession:
    timeout = ClientTimeout(total=None, connect=config.proxy_connect_timeout_seconds)
    if config.proxy_enabled:
        if not config.proxy_url.startswith(SUPPORTED_PROXY_SCHEMES):
            raise ValueError('PROXY_URL must start with socks5:// or socks5h://')
        
        proxy = 'socks5://' + config.proxy_url[len('socks5h://'):] if config.proxy_url.startswith('socks5h://') else config.proxy_url
        session = AiohttpSession(proxy=proxy, timeout=timeout)
        session.raccoon_original_proxy_url = config.proxy_url
        return session
    return AiohttpSession(timeout=timeout)
