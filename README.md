# Telegram Channel Poster

Автоматический Telegram-бот для ведения канала: администратор отправляет в личку боту много медиа, бот молча сохраняет их в постоянную SQLite-очередь и публикует по одному посту раз в 3 часа.

## Возможности

- Поддерживает `photo`, `video`, `animation` и изображения, отправленные как `document`.
- Альбомы Telegram не публикуются альбомами: каждый элемент сохраняется отдельным FIFO-постом.
- Очередь переживает рестарт и падение прокси.
- При старте элемент со статусом `publishing` возвращается в `queued`.
- После простоя публикуется максимум один пост, затем снова ожидание интервала.
- Все запросы к Telegram идут через SOCKS5 при `PROXY_ENABLED=true`.
- Нет кнопок, предпросмотра и подтверждений после каждого файла.

## Создание бота

1. Откройте [@BotFather](https://t.me/BotFather).
2. Выполните `/newbot` и сохраните токен в `BOT_TOKEN`.
3. Добавьте бота администратором в целевой канал с правом публикации сообщений.

## TARGET_CHANNEL_ID

- Для публичного канала можно указать `@username`.
- Для приватного канала используйте числовой id вида `-1001234567890`. Его можно получить через служебных ботов или временно переслав сообщение из канала в бота, который показывает chat id.

## ADMIN_IDS

Напишите [@userinfobot](https://t.me/userinfobot) или аналогичному боту и скопируйте свой числовой Telegram id. Несколько администраторов указываются через запятую.

## Настройка `.env`

Скопируйте `.env.example` в `.env` и заполните значения:

```env
BOT_TOKEN=123456:token
TARGET_CHANNEL_ID=@your_channel
ADMIN_IDS=123456789
POST_INTERVAL_HOURS=3
DATABASE_PATH=data/bot.db
TIMEZONE=Europe/Moscow
PROXY_ENABLED=true
PROXY_URL=socks5h://127.0.0.1:1080
PROXY_CONNECT_TIMEOUT_SECONDS=30
BATCH_NOTIFICATION_ENABLED=true
BATCH_NOTIFICATION_DELAY_SECONDS=5
LOG_LEVEL=INFO
```

`PROXY_URL` поддерживает `socks5://` и `socks5h://`. Для локального sing-box обычно используется `socks5h://127.0.0.1:1080`.

## Локальный запуск

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m bot.main
```

## systemd

Пример unit-файла находится в `systemd/raccoon-channel-poster.service` и запускается после `raccoon-sing-box.service`:

```ini
After=network-online.target raccoon-sing-box.service
Requires=raccoon-sing-box.service
```

Установка:

```bash
sudo cp systemd/raccoon-channel-poster.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now raccoon-channel-poster.service
journalctl -u raccoon-channel-poster.service -f
```

## Команды

- `/start` — краткая инструкция.
- `/status` — статус публикации, размер очереди, следующий запуск, последний успешный пост.
- `/queue` — размер очереди и примерный запас в днях.
- `/pause` — приостановить автопубликацию.
- `/resume` — возобновить автопубликацию.
- `/next` — немедленно опубликовать следующий пост и перенести следующий автозапуск на интервал.
- `/skip` — пропустить следующий элемент.
- `/clear confirm` — очистить очередь.
- `/help` — список команд.

## Резервное копирование SQLite

```bash
sqlite3 data/bot.db ".backup 'backup/bot-$(date +%F).db'"
```

Перед восстановлением остановите сервис:

```bash
sudo systemctl stop raccoon-channel-poster.service
cp backup/bot-YYYY-MM-DD.db data/bot.db
sudo systemctl start raccoon-channel-poster.service
```

## Проверка

```bash
pytest
```
