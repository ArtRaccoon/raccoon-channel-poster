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
        signature TEXT,
        default_buttons_json TEXT,
        channel_timezone TEXT,
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
        buttons_json TEXT,
        media_json TEXT,
        album_group_id TEXT,
        status TEXT DEFAULT 'draft',
        use_signature INTEGER DEFAULT 1,
        repeat_enabled INTEGER DEFAULT 0,
        repeat_interval_minutes INTEGER,
        repeat_until TEXT,
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
    '''
    CREATE TABLE IF NOT EXISTS signature_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_telegram_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        text TEXT NOT NULL,
        created_at TEXT
    )
    ''',
    '''
    CREATE TABLE IF NOT EXISTS channel_schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_telegram_id INTEGER NOT NULL,
        channel_id TEXT NOT NULL,
        weekday INTEGER NOT NULL,
        time TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
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
        await _ensure_column(db, 'posts', 'buttons_json', 'ALTER TABLE posts ADD COLUMN buttons_json TEXT')
        await _ensure_column(db, 'posts', 'media_json', 'ALTER TABLE posts ADD COLUMN media_json TEXT')
        await _ensure_column(db, 'posts', 'album_group_id', 'ALTER TABLE posts ADD COLUMN album_group_id TEXT')
        await _ensure_column(db, 'posts', 'use_signature', 'ALTER TABLE posts ADD COLUMN use_signature INTEGER DEFAULT 1')
        await _ensure_column(db, 'posts', 'repeat_enabled', 'ALTER TABLE posts ADD COLUMN repeat_enabled INTEGER DEFAULT 0')
        await _ensure_column(db, 'posts', 'repeat_interval_minutes', 'ALTER TABLE posts ADD COLUMN repeat_interval_minutes INTEGER')
        await _ensure_column(db, 'posts', 'repeat_until', 'ALTER TABLE posts ADD COLUMN repeat_until TEXT')

        await _ensure_column(db, 'channels', 'is_active', 'ALTER TABLE channels ADD COLUMN is_active INTEGER DEFAULT 1')
        await _ensure_column(db, 'channels', 'signature', 'ALTER TABLE channels ADD COLUMN signature TEXT')
        await _ensure_column(db, 'channels', 'default_buttons_json', 'ALTER TABLE channels ADD COLUMN default_buttons_json TEXT')
        await _ensure_column(db, 'channels', 'channel_timezone', 'ALTER TABLE channels ADD COLUMN channel_timezone TEXT')
        await db.commit()

