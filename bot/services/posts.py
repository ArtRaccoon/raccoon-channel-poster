from datetime import datetime, timezone
import aiosqlite

CAPTION_LIMIT = 1024


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_draft(db_path: str, owner_telegram_id: int, text: str | None, media_file_id: str | None = None, media_type: str = 'text') -> int:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            'INSERT INTO posts (owner_telegram_id, text, media_file_id, media_type, status, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            (owner_telegram_id, text, media_file_id, media_type, 'draft', _now()),
        )
        await db.commit()
        return cur.lastrowid


async def create_post_copy(db_path: str, source_post: tuple, channel_id: str | None = None, status: str = 'draft') -> int:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            '''INSERT INTO posts (owner_telegram_id, channel_id, text, media_file_id, media_type, status, created_at, buttons_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                source_post[1],
                channel_id if channel_id is not None else source_post[2],
                source_post[3],
                source_post[4],
                source_post[5],
                status,
                _now(),
                source_post[10],
            ),
        )
        await db.commit()
        return cur.lastrowid


async def get_post(db_path: str, post_id: int):
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            '''SELECT id, owner_telegram_id, channel_id, text, media_file_id, media_type, status,
                      created_at, published_at, scheduled_at, buttons_json
               FROM posts WHERE id=?''',
            (post_id,),
        )
        return await cur.fetchone()


async def list_recent_posts(db_path: str, owner_telegram_id: int, only_drafts: bool = False):
    async with aiosqlite.connect(db_path) as db:
        query = 'SELECT id, media_type, text, status, created_at FROM posts WHERE owner_telegram_id=?'
        params = [owner_telegram_id]
        if only_drafts:
            query += " AND status='draft'"
        query += ' ORDER BY id DESC LIMIT 10'
        cur = await db.execute(query, params)
        return await cur.fetchall()


async def search_posts(db_path: str, owner_telegram_id: int, query_text: str):
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            '''SELECT id, media_type, text, status, created_at
               FROM posts
               WHERE owner_telegram_id=? AND COALESCE(text, '') LIKE ?
               ORDER BY id DESC LIMIT 10''',
            (owner_telegram_id, f'%{query_text}%'),
        )
        return await cur.fetchall()


async def update_post_text(db_path: str, post_id: int, text: str | None) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute('UPDATE posts SET text=? WHERE id=?', (text, post_id))
        await db.commit()


async def update_post_buttons(db_path: str, post_id: int, owner_telegram_id: int, buttons_json: str | None) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute('UPDATE posts SET buttons_json=? WHERE id=? AND owner_telegram_id=?', (buttons_json, post_id, owner_telegram_id))
        await db.commit()


async def update_post_media(db_path: str, post_id: int, owner_telegram_id: int, media_file_id: str, media_type: str = 'photo') -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            'UPDATE posts SET media_file_id=?, media_type=? WHERE id=? AND owner_telegram_id=?',
            (media_file_id, media_type, post_id, owner_telegram_id),
        )
        await db.commit()


async def set_post_channel(db_path: str, post_id: int, channel_id: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute('UPDATE posts SET channel_id=? WHERE id=?', (channel_id, post_id))
        await db.commit()


async def set_post_status(db_path: str, post_id: int, status: str, channel_id: str | None = None, scheduled_at: str | None = None) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            'UPDATE posts SET status=?, channel_id=COALESCE(?, channel_id), scheduled_at=COALESCE(?, scheduled_at), published_at=CASE WHEN ?="published" THEN ? ELSE published_at END WHERE id=?',
            (status, channel_id, scheduled_at, status, _now(), post_id),
        )
        await db.commit()


async def delete_draft(db_path: str, post_id: int, owner_telegram_id: int) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute('DELETE FROM posts WHERE id=? AND owner_telegram_id=? AND status="draft"', (post_id, owner_telegram_id))
        await db.commit()


async def delete_old_drafts(db_path: str, owner_telegram_id: int, days: int = 30) -> int:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            "DELETE FROM posts WHERE owner_telegram_id=? AND status='draft' AND datetime(created_at) < datetime('now', ?)",
            (owner_telegram_id, f'-{days} days'),
        )
        await db.commit()
        return cur.rowcount


async def get_due_scheduled_posts(db_path: str, now_iso: str):
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            """SELECT id, owner_telegram_id, channel_id, text, media_file_id, media_type, status,
                      created_at, published_at, scheduled_at, buttons_json
               FROM posts
               WHERE status='scheduled' AND scheduled_at IS NOT NULL AND datetime(scheduled_at) <= datetime(?)
               ORDER BY id ASC LIMIT 50""",
            (now_iso,),
        )
        return await cur.fetchall()


async def add_publish_log(db_path: str, owner_telegram_id: int, channel_id: str, post_id: int, status: str, error: str | None = None) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            'INSERT INTO publish_logs (owner_telegram_id, channel_id, post_id, status, error, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            (owner_telegram_id, channel_id, post_id, status, error, _now()),
        )
        await db.commit()


async def latest_publish_errors(db_path: str, limit: int = 10):
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            '''SELECT created_at, owner_telegram_id, channel_id, post_id, error
               FROM publish_logs WHERE status='error'
               ORDER BY id DESC LIMIT ?''',
            (limit,),
        )
        return await cur.fetchall()
