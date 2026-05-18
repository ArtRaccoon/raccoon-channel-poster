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
        published_at TEXT
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


async def init_db(path: str) -> None:
    async with aiosqlite.connect(path) as db:
        for stmt in SCHEMA:
            await db.execute(stmt)
        await db.commit()
