from __future__ import annotations

from html import escape

TELEGRAM_CAPTION_LIMIT = 1024
LINKS_BLOCK = (
    '✏️ <a href="https://t.me/SketchbookAi">Скетчи</a>\n'
    '🎨 <a href="https://t.me/ArtRaccoon">SFW</a>\n'
    '🔞 <a href="https://t.me/podvalArtRaccon">NSFW</a>\n'
    '🦝 <a href="https://t.me/teamArtRaccoon">Команда ArtRaccoon</a>'
)
SEPARATOR = "\n\n"
ELLIPSIS = "…"


def build_caption(user_caption: str | None) -> str:
    escaped = escape(user_caption or "", quote=False).strip()
    if not escaped:
        return LINKS_BLOCK
    overhead = len(SEPARATOR) + len(LINKS_BLOCK)
    available = TELEGRAM_CAPTION_LIMIT - overhead
    if available <= 0:
        return LINKS_BLOCK[-TELEGRAM_CAPTION_LIMIT:]
    if len(escaped) > available:
        escaped = escaped[: max(0, available - len(ELLIPSIS))].rstrip() + ELLIPSIS
    return f"{escaped}{SEPARATOR}{LINKS_BLOCK}"
