import aiosqlite

SCHEMA = [
    '''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        first_name TEXT,
        created_at TEXT,
        last_seen_at TEXT
    )
    ''',
    '''
    CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_telegram_id INTEGER NOT NULL,
        channel_id TEXT NOT NULL,
        title TEXT,
        username TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT,
        UNIQUE(owner_telegram_id, channel_id)
    )
    ''',
    '''
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_telegram_id INTEGER NOT NULL,
        channel_id TEXT,
        text TEXT,
        media_file_id TEXT,
        media_type TEXT,
        status TEXT DEFAULT 'draft',
        created_at TEXT,
        published_at TEXT,
        scheduled_at TEXT
    )
    ''',
    '''
    CREATE TABLE IF NOT EXISTS publish_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_telegram_id INTEGER,
        channel_id TEXT,
        post_id INTEGER,
        status TEXT,
        error TEXT,
        created_at TEXT
    )
    ''',
]


async def _ensure_column(db, table: str, column: str, ddl: str) -> None:
    cols = await (await db.execute(f'PRAGMA table_info({table})')).fetchall()
    names = {c[1] for c in cols}
    if column not in names:
        await db.execute(ddl)


async def init_db(path: str) -> None:
    async with aiosqlite.connect(path) as db:
        for stmt in SCHEMA:
            await db.execute(stmt)
        await _ensure_column(db, 'posts', 'media_file_id', 'ALTER TABLE posts ADD COLUMN media_file_id TEXT')
        await _ensure_column(db, 'posts', 'media_type', 'ALTER TABLE posts ADD COLUMN media_type TEXT')
        await _ensure_column(db, 'posts', 'scheduled_at', 'ALTER TABLE posts ADD COLUMN scheduled_at TEXT')
        await _ensure_column(db, 'channels', 'is_active', 'ALTER TABLE channels ADD COLUMN is_active INTEGER DEFAULT 1')
        await db.commit()
