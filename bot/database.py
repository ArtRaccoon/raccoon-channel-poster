from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import aiosqlite

SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS queue_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        media_type TEXT NOT NULL,
        file_id TEXT NOT NULL,
        caption TEXT,
        message_id INTEGER,
        update_id INTEGER,
        media_group_id TEXT,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'queued',
        attempts INTEGER NOT NULL DEFAULT 0,
        error TEXT,
        published_at TEXT,
        UNIQUE(file_id, message_id, update_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_queue_status_id ON queue_items(status, id)",
    """
    CREATE TABLE IF NOT EXISTS bot_state (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """,
)

LEGACY_TABLES = (
    "users",
    "channels",
    "posts",
    "post_batches",
    "channel_schedules",
    "publish_logs",
    "edit_logs",
)


@dataclass(slots=True)
class QueueItem:
    id: int
    media_type: str
    file_id: str
    caption: str | None
    attempts: int


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def init_db(path: str) -> None:
    async with aiosqlite.connect(path) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        for table in LEGACY_TABLES:
            await db.execute(f"DROP TABLE IF EXISTS {table}")
        for stmt in SCHEMA:
            await db.execute(stmt)
        await db.execute("INSERT OR IGNORE INTO bot_state(key, value) VALUES('paused', '0')")
        await db.commit()


async def recover_publishing(path: str) -> None:
    async with aiosqlite.connect(path) as db:
        await db.execute("UPDATE queue_items SET status='queued', error=NULL WHERE status='publishing'")
        await db.commit()


async def enqueue_media(
    path: str,
    media_type: str,
    file_id: str,
    caption: str | None,
    message_id: int | None,
    update_id: int | None,
    media_group_id: str | None,
) -> bool:
    async with aiosqlite.connect(path) as db:
        cur = await db.execute(
            """
            INSERT OR IGNORE INTO queue_items(
                media_type, file_id, caption, message_id, update_id, media_group_id, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'queued')
            """,
            (media_type, file_id, caption, message_id, update_id, media_group_id, now_iso()),
        )
        await db.commit()
        return cur.rowcount > 0


async def queue_count(path: str) -> int:
    async with aiosqlite.connect(path) as db:
        row = await (await db.execute("SELECT COUNT(*) FROM queue_items WHERE status='queued'")).fetchone()
        return int(row[0])


async def claim_next(path: str) -> QueueItem | None:
    async with aiosqlite.connect(path) as db:
        await db.execute("BEGIN IMMEDIATE")
        row = await (
            await db.execute(
                """
                SELECT id, media_type, file_id, caption, attempts
                FROM queue_items
                WHERE status='queued'
                ORDER BY id
                LIMIT 1
                """
            )
        ).fetchone()
        if not row:
            await db.commit()
            return None
        await db.execute(
            "UPDATE queue_items SET status='publishing', attempts=attempts+1, error=NULL WHERE id=?",
            (row[0],),
        )
        await db.commit()
        return QueueItem(row[0], row[1], row[2], row[3], row[4] + 1)


async def mark_published(path: str, item_id: int) -> None:
    async with aiosqlite.connect(path) as db:
        timestamp = now_iso()
        await db.execute(
            "UPDATE queue_items SET status='published', published_at=?, error=NULL WHERE id=?",
            (timestamp, item_id),
        )
        await db.execute("INSERT OR REPLACE INTO bot_state(key, value) VALUES('last_success_at', ?)", (timestamp,))
        await db.commit()


async def requeue_failed(path: str, item_id: int, error: str) -> None:
    async with aiosqlite.connect(path) as db:
        await db.execute("UPDATE queue_items SET status='queued', error=? WHERE id=?", (error[:500], item_id))
        await db.commit()


async def skip_next(path: str) -> bool:
    item = await claim_next(path)
    if not item:
        return False
    async with aiosqlite.connect(path) as db:
        await db.execute("UPDATE queue_items SET status='skipped' WHERE id=?", (item.id,))
        await db.commit()
    return True


async def clear_queue(path: str) -> int:
    async with aiosqlite.connect(path) as db:
        cur = await db.execute("UPDATE queue_items SET status='skipped' WHERE status IN ('queued', 'publishing')")
        await db.commit()
        return cur.rowcount


async def set_state(path: str, key: str, value: str) -> None:
    async with aiosqlite.connect(path) as db:
        await db.execute("INSERT OR REPLACE INTO bot_state(key, value) VALUES(?, ?)", (key, value))
        await db.commit()


async def get_state(path: str, key: str, default: str | None = None) -> str | None:
    async with aiosqlite.connect(path) as db:
        row = await (await db.execute("SELECT value FROM bot_state WHERE key=?", (key,))).fetchone()
        return row[0] if row else default
