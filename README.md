# raccoon-channel-poster

Telegram posting bot (aiogram 3.x, SQLite, APScheduler) with channel mini-CMS features.

## New features
- Database backup from admin panel (`💾 Бэкап базы`) via SQLite backup API.
- URL buttons per post + default URL buttons per channel.
- Channel signature + channel timezone fields.
- Signature templates table (`signature_templates`).
- Album-ready schema (`media_json`, `album_group_id`) and unified publishing service.
- Post duplication and media/button-oriented draft controls (UI prepared).
- Admin error feed (`🚨 Ошибки`) from `publish_logs`.
- Scheduling foundation: `channel_schedules` table for channel slot planning.

## Safety and migrations
- Safe SQLite migrations with `PRAGMA table_info` + `ALTER TABLE ADD COLUMN`.
- Existing rows are preserved.
- Secrets are not committed (`.env` ignored).
- DB artifacts ignored: `*.db`, `backups/`, `backups/*.db`.

## Publish pipeline
- Shared helper in `bot/services/publishing.py`:
  - `build_post_text_with_signature`
  - `build_url_buttons_markup`
  - `render_post_preview`
  - `publish_post`
  - `classify_publish_error`
  - `validate_post_before_publish`
- Used by manual publish and scheduler.

## Telegram limits
- Text post max: 4096 chars.
- Photo/album caption max: 1024 chars.
- Album inline URL buttons are sent as a separate message after `send_media_group`.

## systemd update flow
1. Pull latest branch.
2. Install/update dependencies.
3. Restart bot service.
4. Check `logs/bot.log`.

## Proxy
- Uses common `PROXY_URL=socks5://127.0.0.1:1080` via `AiohttpSession` (unchanged).
