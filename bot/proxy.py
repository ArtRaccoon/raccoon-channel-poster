from __future__ import annotations

from aiohttp import ClientSession
from aiohttp_socks import ProxyConnector


def create_http_session(proxy_url: str) -> ClientSession:
    if proxy_url:
        connector = ProxyConnector.from_url(proxy_url)
        return ClientSession(connector=connector)
    return ClientSession()
