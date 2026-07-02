from __future__ import annotations

from dataclasses import dataclass
from html import escape

LINKS_BLOCK_MARKER = '✦ Полезные ссылки'
TEXT_LIMIT = 4096
CAPTION_LIMIT = 1024


@dataclass(frozen=True)
class AppendResult:
    text: str
    changed: bool
    reason: str | None = None


def build_links_quote_block(links_block: str) -> str:
    """Build a Telegram HTML blockquote with escaped useful links text."""
    cleaned = (links_block or '').strip()
    if not cleaned:
        return ''
    escaped_lines = [escape(LINKS_BLOCK_MARKER)]
    escaped_lines.extend(escape(line.rstrip()) for line in cleaned.splitlines() if line.strip())
    return '<blockquote>\n' + '\n'.join(escaped_lines) + '\n</blockquote>'


def append_links_block(original_text: str, links_block: str) -> str:
    result = append_links_block_checked(original_text, links_block)
    return result.text


def append_links_block_checked(original_text: str, links_block: str, *, limit: int | None = None) -> AppendResult:
    """Escape original text and append the links block once.

    Returns changed=False when there is no links block, marker already exists,
    or the resulting text would exceed the provided Telegram limit.
    """
    original_text = original_text or ''
    if not (links_block or '').strip():
        return AppendResult(original_text, False, 'skipped_no_links')
    if LINKS_BLOCK_MARKER in original_text:
        return AppendResult(original_text, False, 'skipped_already_has_block')

    quote_block = build_links_quote_block(links_block)
    new_text = f'{escape(original_text)}\n\n{quote_block}' if original_text else quote_block
    if limit is not None and len(new_text) > limit:
        return AppendResult(original_text, False, 'error_limit')
    return AppendResult(new_text, True)
