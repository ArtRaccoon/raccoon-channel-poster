from aiogram.client.session.aiohttp import AiohttpSession


def build_session(proxy_url: str) -> AiohttpSession:
    if proxy_url.strip():
        return AiohttpSession(proxy=proxy_url)
    return AiohttpSession()
