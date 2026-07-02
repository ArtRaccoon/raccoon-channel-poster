from __future__ import annotations

from datetime import datetime, timezone

import aiosqlite


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def add_edit_log(
    db_path: str,
    owner_telegram_id: int | None,
    channel_id: str,
    message_id: int | None,
    status: str,
    error: str | None = None,
) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            '''INSERT INTO edit_logs (owner_telegram_id, channel_id, message_id, status, error, created_at)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (owner_telegram_id, channel_id, message_id, status, error, _now()),
        )
        await db.commit()


async def list_recent_edit_logs(db_path: str, limit: int = 10):
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            '''SELECT created_at, owner_telegram_id, channel_id, message_id, status, error
               FROM edit_logs ORDER BY id DESC LIMIT ?''',
            (limit,),
        )
        return await cursor.fetchall()
