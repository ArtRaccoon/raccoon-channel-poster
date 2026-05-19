from datetime import datetime, timezone
import aiosqlite


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_channel_schedule(db_path: str, owner_telegram_id: int, channel_id: str):
    async with aiosqlite.connect(db_path) as db:
        rows = await (await db.execute(
            'SELECT weekday, time FROM channel_schedules WHERE owner_telegram_id=? AND channel_id=? AND is_active=1 ORDER BY weekday, time',
            (owner_telegram_id, channel_id),
        )).fetchall()
        return rows


async def replace_channel_schedule(db_path: str, owner_telegram_id: int, channel_id: str, slots: list[tuple[int, str]]):
    async with aiosqlite.connect(db_path) as db:
        await db.execute('DELETE FROM channel_schedules WHERE owner_telegram_id=? AND channel_id=?', (owner_telegram_id, channel_id))
        for weekday, tm in slots:
            await db.execute(
                'INSERT INTO channel_schedules (owner_telegram_id, channel_id, weekday, time, is_active, created_at) VALUES (?, ?, ?, ?, 1, ?)',
                (owner_telegram_id, channel_id, weekday, tm, _now()),
            )
        await db.commit()


async def clear_channel_schedule(db_path: str, owner_telegram_id: int, channel_id: str):
    async with aiosqlite.connect(db_path) as db:
        await db.execute('DELETE FROM channel_schedules WHERE owner_telegram_id=? AND channel_id=?', (owner_telegram_id, channel_id))
        await db.commit()
