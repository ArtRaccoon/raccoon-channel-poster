from datetime import datetime, timezone
import random
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
        query = "SELECT channel_id, title, username, is_active, signature, signature_2, signature_3, signature_mode, signature_rotate_index FROM channels WHERE owner_telegram_id=?"
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


async def get_channel_signature(db_path: str, owner_telegram_id: int, channel_id: str | None, for_publish: bool = False) -> str | None:
    if not channel_id:
        return None
    async with aiosqlite.connect(db_path) as db:
        row = await (await db.execute(
            'SELECT signature, signature_2, signature_3, signature_mode, signature_rotate_index FROM channels WHERE owner_telegram_id=? AND channel_id=? AND is_active=1',
            (owner_telegram_id, channel_id),
        )).fetchone()
        if not row:
            return None
        signatures = [s.strip() for s in row[:3] if isinstance(s, str) and s.strip()]
        mode = row[3] or 'first'
        rotate_index = int(row[4] or 0)
        if not signatures:
            return None
        if mode == 'random':
            return random.choice(signatures)
        if mode == 'rotate':
            idx = rotate_index % len(signatures)
            sign = signatures[idx]
            if for_publish:
                await db.execute('UPDATE channels SET signature_rotate_index=? WHERE owner_telegram_id=? AND channel_id=?', (rotate_index + 1, owner_telegram_id, channel_id))
                await db.commit()
            return sign
        return signatures[0]


async def set_channel_signature(db_path: str, owner_telegram_id: int, channel_id: str, signature: str | None, slot: int = 1) -> None:
    col = 'signature' if slot == 1 else f'signature_{slot}'
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            f'UPDATE channels SET {col}=? WHERE owner_telegram_id=? AND channel_id=? AND is_active=1',
            (signature, owner_telegram_id, channel_id),
        )
        await db.commit()


async def set_channel_signature_mode(db_path: str, owner_telegram_id: int, channel_id: str, mode: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute('UPDATE channels SET signature_mode=? WHERE owner_telegram_id=? AND channel_id=? AND is_active=1', (mode, owner_telegram_id, channel_id))
        await db.commit()


async def clear_channel_signatures(db_path: str, owner_telegram_id: int, channel_id: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            'UPDATE channels SET signature=NULL, signature_2=NULL, signature_3=NULL, signature_rotate_index=0 WHERE owner_telegram_id=? AND channel_id=? AND is_active=1',
            (owner_telegram_id, channel_id),
        )
        await db.commit()
