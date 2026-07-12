from __future__ import annotations

import aiosqlite
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from .models import ChannelSettings, QueueItem


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: str):
        self.path = path

    async def _open(self) -> aiosqlite.Connection:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        db = await aiosqlite.connect(self.path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        return db

    @asynccontextmanager
    async def connect(self):
        db = await self._open()
        try:
            yield db
        finally:
            await db.close()

    async def init(self) -> None:
        async with self.connect() as db:
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS queue_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_chat_id INTEGER NOT NULL,
                    source_message_id INTEGER NOT NULL,
                    media_group_id TEXT,
                    media_type TEXT NOT NULL,
                    file_id TEXT NOT NULL,
                    caption TEXT,
                    status TEXT NOT NULL DEFAULT 'queued',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    published_at TEXT,
                    UNIQUE(source_chat_id, source_message_id)
                );
                CREATE INDEX IF NOT EXISTS idx_queue_fifo ON queue_items(status, created_at, source_message_id, id);
                CREATE TABLE IF NOT EXISTS bot_state (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                CREATE TABLE IF NOT EXISTS bot_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                """
            )
            for key, value in {"paused": "false", "next_run_at": "", "last_success_at": "", "last_error": ""}.items():
                await db.execute("INSERT OR IGNORE INTO bot_state(key, value) VALUES(?, ?)", (key, value))
            await db.commit()


    async def restore_publishing(self) -> int:
        async with self.connect() as db:
            cur = await db.execute("UPDATE queue_items SET status='queued' WHERE status='publishing'")
            await db.commit()
            return cur.rowcount

    async def add_item(self, source_chat_id:int, source_message_id:int, media_group_id:str|None, media_type:str, file_id:str, caption:str|None) -> bool:
        async with self.connect() as db:
            cur = await db.execute(
                """INSERT OR IGNORE INTO queue_items(source_chat_id, source_message_id, media_group_id, media_type, file_id, caption, status, created_at)
                VALUES(?,?,?,?,?,?, 'queued', ?)""",
                (source_chat_id, source_message_id, media_group_id, media_type, file_id, caption, utcnow()),
            )
            await db.commit()
            return cur.rowcount == 1

    async def add_many(self, items:list[tuple[int,int,str|None,str,str,str|None]]) -> int:
        count=0
        for item in sorted(items, key=lambda x: x[1]):
            if await self.add_item(*item): count += 1
        return count

    async def claim_next(self) -> QueueItem | None:
        async with self.connect() as db:
            await db.execute("BEGIN IMMEDIATE")
            cur = await db.execute("SELECT * FROM queue_items WHERE status='queued' ORDER BY created_at, source_message_id, id LIMIT 1")
            row = await cur.fetchone()
            if not row:
                await db.commit()
                return None
            await db.execute("UPDATE queue_items SET status='publishing', attempts=attempts+1, last_error=NULL WHERE id=?", (row["id"],))
            await db.commit()
            cur = await db.execute("SELECT * FROM queue_items WHERE id=?", (row["id"],))
            return QueueItem(**dict(await cur.fetchone()))

    async def mark_published(self, item_id:int) -> None:
        async with self.connect() as db:
            await db.execute("UPDATE queue_items SET status='published', published_at=? WHERE id=?", (utcnow(), item_id)); await db.commit()

    async def release_failed(self, item_id:int, error:str) -> None:
        async with self.connect() as db:
            await db.execute("UPDATE queue_items SET status='queued', last_error=? WHERE id=?", (error[:500], item_id))
            await db.execute("INSERT OR REPLACE INTO bot_state(key,value) VALUES('last_error', ?)", (error[:500],)); await db.commit()

    async def skip_next(self) -> bool:
        item = await self.claim_next()
        if not item: return False
        async with self.connect() as db:
            await db.execute("UPDATE queue_items SET status='skipped' WHERE id=?", (item.id,)); await db.commit()
        return True

    async def clear_pending(self) -> int:
        async with self.connect() as db:
            cur=await db.execute("UPDATE queue_items SET status='skipped' WHERE status IN ('queued','publishing')")
            await db.commit(); return cur.rowcount

    async def count_queued(self) -> int:
        async with self.connect() as db:
            cur=await db.execute("SELECT COUNT(*) FROM queue_items WHERE status='queued'"); return (await cur.fetchone())[0]

    async def get_state(self, key:str) -> str:
        async with self.connect() as db:
            cur=await db.execute("SELECT value FROM bot_state WHERE key=?", (key,)); row=await cur.fetchone(); return row[0] if row else ""

    async def set_state(self, key:str, value:str) -> None:
        async with self.connect() as db:
            await db.execute("INSERT OR REPLACE INTO bot_state(key,value) VALUES(?,?)", (key,value)); await db.commit()

    async def paused(self) -> bool:
        return (await self.get_state("paused")).lower() == "true"

    async def set_paused(self, paused:bool) -> None:
        await self.set_state("paused", "true" if paused else "false")

    async def get_channel(self) -> ChannelSettings | None:
        async with self.connect() as db:
            cur = await db.execute("SELECT key, value FROM bot_settings WHERE key IN ('channel_id', 'channel_username', 'channel_title')")
            values = {row["key"]: row["value"] for row in await cur.fetchall()}
        if not values.get("channel_id"):
            return None
        return ChannelSettings(
            channel_id=int(values["channel_id"]),
            channel_username=values.get("channel_username") or None,
            channel_title=values.get("channel_title") or None,
        )

    async def set_channel(self, channel: ChannelSettings) -> None:
        async with self.connect() as db:
            await db.executemany(
                "INSERT OR REPLACE INTO bot_settings(key, value) VALUES(?, ?)",
                [
                    ("channel_id", str(channel.channel_id)),
                    ("channel_username", channel.channel_username or ""),
                    ("channel_title", channel.channel_title or ""),
                ],
            )
            await db.commit()

    async def remove_channel(self) -> None:
        async with self.connect() as db:
            await db.execute("DELETE FROM bot_settings WHERE key IN ('channel_id', 'channel_username', 'channel_title')")
            await db.commit()
