from datetime import datetime, timezone
import aiosqlite

CAPTION_LIMIT = 1024
TEXT_LIMIT = 4096


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_draft(db_path: str, owner_telegram_id: int, text: str | None, media_file_id: str | None = None, media_type: str = 'text', media_json: str | None = None, album_group_id: str | None = None) -> int:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            'INSERT INTO posts (owner_telegram_id, text, media_file_id, media_type, media_json, album_group_id, status, created_at, use_signature, repeat_enabled, repeat_until) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (owner_telegram_id, text, media_file_id, media_type, media_json, album_group_id, 'draft', _now(), 1, 0, None),
        )
        await db.commit()
        return cur.lastrowid


async def get_post(db_path: str, post_id: int):
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute('SELECT id, owner_telegram_id, channel_id, text, media_file_id, media_type, status, created_at, published_at, scheduled_at, buttons_json, media_json, album_group_id, use_signature, repeat_enabled, repeat_interval_minutes, repeat_until FROM posts WHERE id=?', (post_id,))
        return await cur.fetchone()


async def list_recent_posts(db_path: str, owner_telegram_id: int, only_drafts: bool = False):
    async with aiosqlite.connect(db_path) as db:
        query = 'SELECT id, media_type, text, status, created_at FROM posts WHERE owner_telegram_id=?'
        params = [owner_telegram_id]
        if only_drafts:
            query += " AND status='draft'"
        query += ' ORDER BY id DESC LIMIT 10'
        return await (await db.execute(query, params)).fetchall()


async def list_drafts_without_schedule_for_channel(db_path: str, owner_telegram_id: int, channel_id: str):
    async with aiosqlite.connect(db_path) as db:
        return await (await db.execute(
            "SELECT id FROM posts WHERE owner_telegram_id=? AND status='draft' AND scheduled_at IS NULL AND channel_id=? ORDER BY id ASC",
            (owner_telegram_id, channel_id),
        )).fetchall()


async def search_posts(db_path: str, owner_telegram_id: int, query: str):
    async with aiosqlite.connect(db_path) as db:
        return await (await db.execute(
            "SELECT id, status, media_type, text FROM posts WHERE owner_telegram_id=? AND COALESCE(text,'') LIKE ? ORDER BY id DESC LIMIT 10",
            (owner_telegram_id, f'%{query}%'),
        )).fetchall()


async def update_post_text(db_path: str, post_id: int, text: str | None) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute('UPDATE posts SET text=? WHERE id=?', (text, post_id))
        await db.commit()


async def update_post_buttons(db_path: str, post_id: int, buttons_json: str | None) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute('UPDATE posts SET buttons_json=? WHERE id=?', (buttons_json, post_id))
        await db.commit()


async def update_post_media(db_path: str, post_id: int, media_type: str, media_file_id: str | None = None, media_json: str | None = None, album_group_id: str | None = None):
    async with aiosqlite.connect(db_path) as db:
        await db.execute('UPDATE posts SET media_type=?, media_file_id=?, media_json=?, album_group_id=? WHERE id=?', (media_type, media_file_id, media_json, album_group_id, post_id))
        await db.commit()


async def duplicate_post(db_path: str, post_id: int, owner_telegram_id: int) -> int:
    async with aiosqlite.connect(db_path) as db:
        src = await (await db.execute('SELECT text, media_file_id, media_type, media_json, buttons_json, channel_id FROM posts WHERE id=? AND owner_telegram_id=?', (post_id, owner_telegram_id))).fetchone()
        cur = await db.execute('INSERT INTO posts (owner_telegram_id, text, media_file_id, media_type, media_json, buttons_json, channel_id, status, created_at, scheduled_at, published_at) VALUES (?, ?, ?, ?, ?, ?, ?, "draft", ?, NULL, NULL)', (owner_telegram_id, *src, _now()))
        await db.commit()
        return cur.lastrowid


async def set_post_channel(db_path: str, post_id: int, channel_id: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute('UPDATE posts SET channel_id=? WHERE id=?', (channel_id, post_id))
        await db.commit()


async def set_post_status(db_path: str, post_id: int, status: str, channel_id: str | None = None, scheduled_at: str | None = None) -> None:
    async with aiosqlite.connect(db_path) as db:
        if status == 'scheduled':
            if not scheduled_at:
                raise ValueError('scheduled_at is required for scheduled status')
            await db.execute(
                'UPDATE posts SET status=?, channel_id=COALESCE(?, channel_id), scheduled_at=? WHERE id=?',
                (status, channel_id, scheduled_at, post_id),
            )
        elif status == 'draft':
            await db.execute(
                'UPDATE posts SET status=?, channel_id=COALESCE(?, channel_id), scheduled_at=NULL WHERE id=?',
                (status, channel_id, post_id),
            )
        elif status == 'published':
            await db.execute(
                'UPDATE posts SET status=?, channel_id=COALESCE(?, channel_id), published_at=?, scheduled_at=NULL WHERE id=?',
                (status, channel_id, _now(), post_id),
            )
        elif status == 'failed':
            await db.execute(
                'UPDATE posts SET status=?, channel_id=COALESCE(?, channel_id) WHERE id=?',
                (status, channel_id, post_id),
            )
        else:
            await db.execute(
                'UPDATE posts SET status=?, channel_id=COALESCE(?, channel_id) WHERE id=?',
                (status, channel_id, post_id),
            )
        await db.commit()


async def unset_schedule(db_path: str, post_id: int, owner_telegram_id: int):
    async with aiosqlite.connect(db_path) as db:
        await db.execute("UPDATE posts SET status='draft', scheduled_at=NULL WHERE id=? AND owner_telegram_id=?", (post_id, owner_telegram_id))
        await db.commit()


async def delete_old_drafts(db_path: str, owner_telegram_id: int, older_than_iso: str):
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute('DELETE FROM posts WHERE owner_telegram_id=? AND status="draft" AND datetime(created_at) < datetime(?)', (owner_telegram_id, older_than_iso))
        await db.commit()
        return cur.rowcount


async def delete_draft(db_path: str, post_id: int, owner_telegram_id: int) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute('DELETE FROM posts WHERE id=? AND owner_telegram_id=? AND status="draft"', (post_id, owner_telegram_id))
        await db.commit()


async def get_due_scheduled_posts(db_path: str, now_iso: str):
    async with aiosqlite.connect(db_path) as db:
        return await (await db.execute(
            "SELECT id FROM posts WHERE status='scheduled' AND scheduled_at IS NOT NULL AND datetime(scheduled_at) <= datetime(?) ORDER BY id ASC LIMIT 50",
            (now_iso,),
        )).fetchall()


async def add_publish_log(db_path: str, owner_telegram_id: int, channel_id: str, post_id: int, status: str, error: str | None = None) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute('INSERT INTO publish_logs (owner_telegram_id, channel_id, post_id, status, error, created_at) VALUES (?, ?, ?, ?, ?, ?)', (owner_telegram_id, channel_id, post_id, status, error, _now()))
        await db.commit()


async def set_post_use_signature(db_path: str, post_id: int, use_signature: int):
    async with aiosqlite.connect(db_path) as db:
        await db.execute('UPDATE posts SET use_signature=? WHERE id=?', (use_signature, post_id))
        await db.commit()
