from __future__ import annotations
from html import escape

CAPTION_LIMIT = 1024
LINKS_BLOCK = (
    '✏️ <a href="https://t.me/SketchbookAi">Скетчи</a>\n\n'
    '🎨 <a href="https://t.me/ArtRaccoon">SFW</a>\n\n'
    '🔞 <a href="https://t.me/podvalArtRaccon">NSFW</a>\n\n'
    '🦝 <a href="https://t.me/teamArtRaccoon">Команда ArtRaccoon</a>'
)


def build_caption(user_caption: str | None, limit: int = CAPTION_LIMIT) -> str:
    escaped = escape(user_caption or '', quote=False).strip()
    suffix = LINKS_BLOCK
    if not escaped:
        return suffix
    sep = '\n\n'
    room = limit - len(sep) - len(suffix)
    if room <= 0:
        return suffix[-limit:]
    if len(escaped) > room:
        marker = '…'
        escaped = escaped[: max(0, room - len(marker))].rstrip() + marker
    return f'{escaped}{sep}{suffix}'
