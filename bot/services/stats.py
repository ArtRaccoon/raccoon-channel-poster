import aiosqlite


async def get_admin_stats(db_path: str) -> dict:
    async with aiosqlite.connect(db_path) as db:
        async def q(sql: str):
            return (await (await db.execute(sql)).fetchone())[0]
        total_users = await q('SELECT COUNT(*) FROM users')
        new_users_24h = await q("SELECT COUNT(*) FROM users WHERE datetime(created_at)>=datetime('now','-1 day')")
        new_users_7d = await q("SELECT COUNT(*) FROM users WHERE datetime(created_at)>=datetime('now','-7 day')")
        total_channels = await q('SELECT COUNT(*) FROM channels')
        active_channels = await q('SELECT COUNT(*) FROM channels WHERE is_active=1')
        disabled_channels = await q('SELECT COUNT(*) FROM channels WHERE is_active=0')
        total_posts = await q('SELECT COUNT(*) FROM posts')
        drafts = await q("SELECT COUNT(*) FROM posts WHERE status='draft'")
        scheduled = await q("SELECT COUNT(*) FROM posts WHERE status='scheduled'")
        published = await q("SELECT COUNT(*) FROM posts WHERE status='published'")
        failed = await q("SELECT COUNT(*) FROM posts WHERE status='failed'")
        published_24h = await q("SELECT COUNT(*) FROM posts WHERE status='published' AND datetime(published_at)>=datetime('now','-1 day')")
        published_7d = await q("SELECT COUNT(*) FROM posts WHERE status='published' AND datetime(published_at)>=datetime('now','-7 day')")
        top_channels = await (await db.execute(
            'SELECT owner_telegram_id, COUNT(*) as cnt FROM channels GROUP BY owner_telegram_id ORDER BY cnt DESC LIMIT 5'
        )).fetchall()
        top_pubs = await (await db.execute(
            "SELECT owner_telegram_id, COUNT(*) as cnt FROM posts WHERE status='published' GROUP BY owner_telegram_id ORDER BY cnt DESC LIMIT 5"
        )).fetchall()
    return locals()


async def latest_users(db_path: str):
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            '''SELECT u.telegram_id, u.username, u.first_name,
                      (SELECT COUNT(*) FROM channels c WHERE c.owner_telegram_id=u.telegram_id),
                      (SELECT COUNT(*) FROM posts p WHERE p.owner_telegram_id=u.telegram_id)
               FROM users u ORDER BY u.id DESC LIMIT 10'''
        )
        return await cur.fetchall()


async def latest_channels(db_path: str):
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute('SELECT title, channel_id, owner_telegram_id, is_active FROM channels ORDER BY id DESC LIMIT 10')
        return await cur.fetchall()
