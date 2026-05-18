from datetime import datetime, timezone
import aiosqlite


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def add_channel(db_path: str, owner_telegram_id: int, channel_id: str, title: str | None, username: str | None) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            '''INSERT OR REPLACE INTO channels (owner_telegram_id, channel_id, title, username, is_active, created_at)
               VALUES (?, ?, ?, ?, 1, ?)''',
            (owner_telegram_id, channel_id, title, username, _now()),
        )
        await db.commit()


async def list_user_channels(db_path: str, owner_telegram_id: int, only_active: bool = True):
    async with aiosqlite.connect(db_path) as db:
        query = 'SELECT channel_id, title, username, is_active FROM channels WHERE owner_telegram_id=?'
        if only_active:
            query += ' AND is_active=1'
        query += ' ORDER BY id DESC'
        cursor = await db.execute(query, (owner_telegram_id,))
        return await cursor.fetchall()


async def deactivate_channel(db_path: str, owner_telegram_id: int, channel_id: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute('UPDATE channels SET is_active=0 WHERE owner_telegram_id=? AND channel_id=?', (owner_telegram_id, channel_id))
        await db.commit()


async def has_user_channel(db_path: str, owner_telegram_id: int, channel_id: str) -> bool:
    async with aiosqlite.connect(db_path) as db:
        row = await (await db.execute(
            'SELECT 1 FROM channels WHERE owner_telegram_id=? AND channel_id=? AND is_active=1',
            (owner_telegram_id, channel_id),
        )).fetchone()
        return bool(row)
