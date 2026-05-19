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
        signature TEXT,
        signature_2 TEXT,
        signature_3 TEXT,
        signature_mode TEXT DEFAULT 'first',
        signature_rotate_index INTEGER DEFAULT 0,
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
        media_json TEXT,
        status TEXT DEFAULT 'draft',
        created_at TEXT,
        published_at TEXT,
        scheduled_at TEXT,
        buttons_json TEXT
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
        await _ensure_column(db, 'posts', 'buttons_json', 'ALTER TABLE posts ADD COLUMN buttons_json TEXT')
        await _ensure_column(db, 'posts', 'media_json', 'ALTER TABLE posts ADD COLUMN media_json TEXT')
        await _ensure_column(db, 'channels', 'is_active', 'ALTER TABLE channels ADD COLUMN is_active INTEGER DEFAULT 1')
        await _ensure_column(db, 'channels', 'signature', 'ALTER TABLE channels ADD COLUMN signature TEXT')
        await _ensure_column(db, 'channels', 'signature_2', 'ALTER TABLE channels ADD COLUMN signature_2 TEXT')
        await _ensure_column(db, 'channels', 'signature_3', 'ALTER TABLE channels ADD COLUMN signature_3 TEXT')
        await _ensure_column(db, 'channels', 'signature_mode', "ALTER TABLE channels ADD COLUMN signature_mode TEXT DEFAULT 'first'")
        await _ensure_column(db, 'channels', 'signature_rotate_index', 'ALTER TABLE channels ADD COLUMN signature_rotate_index INTEGER DEFAULT 0')
        await db.commit()
