from datetime import datetime, timezone
import aiosqlite


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def upsert_user(db_path: str, telegram_id: int, username: str | None, first_name: str | None) -> None:
    now = _now()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            '''
            INSERT INTO users (telegram_id, username, first_name, created_at, last_seen_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
              username=excluded.username,
              first_name=excluded.first_name,
              last_seen_at=excluded.last_seen_at
            ''',
            (telegram_id, username, first_name, now, now),
        )
        await db.commit()
