from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from aiogram.client.session.aiohttp import AiohttpSession


def safe_proxy_url(url: str) -> str:
    parts = urlsplit(url)
    netloc = parts.hostname or ""
    if parts.port:
        netloc += f":{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, "", ""))


def create_session(proxy_enabled: bool, proxy_url: str, timeout_seconds: float) -> AiohttpSession:
    if not proxy_enabled:
        return AiohttpSession(timeout=timeout_seconds)
    return AiohttpSession(proxy=proxy_url, timeout=timeout_seconds)
