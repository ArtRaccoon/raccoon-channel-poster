import aiosqlite


async def get_admin_stats(db_path: str) -> dict:
    async with aiosqlite.connect(db_path) as db:
        total_users = (await (await db.execute('SELECT COUNT(*) FROM users')).fetchone())[0]
        total_channels = (await (await db.execute('SELECT COUNT(*) FROM channels')).fetchone())[0]
        total_posts = (await (await db.execute('SELECT COUNT(*) FROM posts')).fetchone())[0]
        published_posts = (await (await db.execute("SELECT COUNT(*) FROM posts WHERE status='published'" )).fetchone())[0]
        publish_errors = (await (await db.execute("SELECT COUNT(*) FROM publish_logs WHERE status='error'" )).fetchone())[0]
        new_users_24h = (await (await db.execute("SELECT COUNT(*) FROM users WHERE datetime(created_at) >= datetime('now','-1 day')")).fetchone())[0]
    return {
        'total_users': total_users,
        'total_channels': total_channels,
        'total_posts': total_posts,
        'published_posts': published_posts,
        'publish_errors': publish_errors,
        'new_users_24h': new_users_24h,
    }


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
        cur = await db.execute(
            'SELECT title, channel_id, owner_telegram_id, is_active FROM channels ORDER BY id DESC LIMIT 10'
        )
        return await cur.fetchall()
