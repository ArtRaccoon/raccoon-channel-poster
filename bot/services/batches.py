from datetime import datetime, timezone
import aiosqlite


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_batch(db_path: str, owner_telegram_id: int, channel_id: str, status: str = 'collecting') -> int:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            'INSERT INTO post_batches (owner_telegram_id, channel_id, status, created_at) VALUES (?, ?, ?, ?)',
            (owner_telegram_id, channel_id, status, _now()),
        )
        await db.commit()
        return cur.lastrowid


async def update_batch_status(db_path: str, batch_id: int, owner_telegram_id: int, status: str):
    async with aiosqlite.connect(db_path) as db:
        await db.execute('UPDATE post_batches SET status=? WHERE id=? AND owner_telegram_id=?', (status, batch_id, owner_telegram_id))
        await db.commit()


async def get_batch(db_path: str, batch_id: int, owner_telegram_id: int):
    async with aiosqlite.connect(db_path) as db:
        return await (await db.execute(
            'SELECT id, owner_telegram_id, channel_id, status, created_at FROM post_batches WHERE id=? AND owner_telegram_id=?',
            (batch_id, owner_telegram_id),
        )).fetchone()
