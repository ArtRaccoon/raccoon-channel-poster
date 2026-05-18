from datetime import datetime, timezone
import aiosqlite


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_draft(db_path: str, owner_telegram_id: int, text: str) -> int:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            'INSERT INTO posts (owner_telegram_id, text, status, created_at) VALUES (?, ?, ?, ?)',
            (owner_telegram_id, text, 'draft', _now()),
        )
        await db.commit()
        return cur.lastrowid


async def mark_published(db_path: str, post_id: int, channel_id: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            'UPDATE posts SET status=?, channel_id=?, published_at=? WHERE id=?',
            ('published', channel_id, _now(), post_id),
        )
        await db.commit()


async def add_publish_log(db_path: str, owner_telegram_id: int, channel_id: str, post_id: int, status: str, error: str | None = None) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            'INSERT INTO publish_logs (owner_telegram_id, channel_id, post_id, status, error, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            (owner_telegram_id, channel_id, post_id, status, error, _now()),
        )
        await db.commit()
