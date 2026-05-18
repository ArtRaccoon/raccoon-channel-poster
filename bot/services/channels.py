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


async def list_user_channels(db_path: str, owner_telegram_id: int):
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            'SELECT channel_id, title, username, is_active FROM channels WHERE owner_telegram_id=? ORDER BY id DESC',
            (owner_telegram_id,),
        )
        return await cursor.fetchall()
