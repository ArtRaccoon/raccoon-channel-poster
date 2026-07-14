from __future__ import annotations

from html import escape

TELEGRAM_CAPTION_LIMIT = 1024
DEFAULT_LINKS_BLOCK = (
    '✏️ <a href="https://t.me/SketchbookAi">Скетчи</a>\n'
    '🎨 <a href="https://t.me/ArtRaccoon">SFW</a>\n'
    '🔞 <a href="https://t.me/podvalArtRaccon">NSFW</a>\n'
    '🦝 <a href="https://t.me/teamArtRaccoon">Команда ArtRaccoon</a>'
)
SEPARATOR = "\n\n"
ELLIPSIS = "…"


def build_caption(user_caption: str | None, links_block: str = DEFAULT_LINKS_BLOCK) -> str:
    escaped = escape(user_caption or "", quote=False).strip()
    links_block = links_block or DEFAULT_LINKS_BLOCK
    if not escaped:
        return links_block[-TELEGRAM_CAPTION_LIMIT:]
    overhead = len(SEPARATOR) + len(links_block)
    available = TELEGRAM_CAPTION_LIMIT - overhead
    if available <= 0:
        return links_block[-TELEGRAM_CAPTION_LIMIT:]
    if len(escaped) > available:
        escaped = escaped[: max(0, available - len(ELLIPSIS))].rstrip() + ELLIPSIS
    return f"{escaped}{SEPARATOR}{links_block}"
