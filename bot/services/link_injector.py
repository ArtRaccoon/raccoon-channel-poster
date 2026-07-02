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


def append_links_block(original_text: str, links_block: str, original_html: str | None = None) -> str:
    result = append_links_block_checked(original_text, links_block, original_html=original_html)
    return result.text


def append_links_block_checked(
    original_text: str,
    links_block: str,
    *,
    original_html: str | None = None,
    limit: int | None = None,
) -> AppendResult:
    """Append the links block once while preserving existing Telegram HTML when available.

    original_text is the plain text/caption used for duplicate marker checks.
    original_html is message.html_text/html_caption when Telegram entities are available;
    if absent, the plain original_text is escaped before appending the block.
    """
    original_text = original_text or ''
    source_html = original_html if original_html is not None else escape(original_text)

    if not (links_block or '').strip():
        return AppendResult(source_html, False, 'skipped_no_links')
    if LINKS_BLOCK_MARKER in original_text or LINKS_BLOCK_MARKER in source_html:
        return AppendResult(source_html, False, 'skipped_already_has_block')

    quote_block = build_links_quote_block(links_block)
    new_text = f'{source_html}\n\n{quote_block}' if source_html else quote_block
    if limit is not None and len(new_text) > limit:
        return AppendResult(source_html, False, 'error_limit')
    return AppendResult(new_text, True)
