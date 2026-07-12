# Raccoon Channel Autoposter

Минималистичный автопостер для одного Telegram-канала. Администраторы отправляют боту медиа в личные сообщения, бот сохраняет их в SQLite-очередь и автоматически публикует по одному элементу через заданный интервал.

## Что осталось в проекте

- Приём `photo`, `video`, `animation` и изображений, отправленных как `document`.
- Постоянная FIFO-очередь в SQLite.
- Восстановление элементов со статусом `publishing` после рестарта.
- Автопубликация по интервалу и ручная публикация следующего элемента.
- Пауза, возобновление, пропуск и очистка очереди.
- SOCKS5/SOCKS5H-прокси для совместимости с локальным sing-box.
- systemd-unit для серверного запуска.

В репозитории нет редактора каналов, FSM-сценариев, клавиатур, черновиков, пакетных публикаций, расписаний старого бота и других legacy-модулей.

## Структура

```text
bot/
  main.py              # точка входа, запуск polling и фонового автопостера
  config.py            # чтение .env
  proxy.py             # aiohttp/aiogram-сессия с SOCKS5/SOCKS5H
  database.py          # SQLite-схема и операции очереди
  publisher.py         # публикация и фоновый цикл
  caption.py           # HTML-caption и блок ссылок
  handlers/
    autoposter.py      # команды и приём медиа
```

## Создание и настройка бота

1. Создайте бота через [@BotFather](https://t.me/BotFather) и сохраните токен в `BOT_TOKEN`.
2. Добавьте бота администратором в целевой канал с правом публикации сообщений.
3. Получите Telegram ID администраторов через [@userinfobot](https://t.me/userinfobot) или аналогичный бот.
4. Заполните `.env`.

## Переменные окружения

```env
BOT_TOKEN=123456:token
TARGET_CHANNEL_ID=@your_channel
ADMIN_IDS=123456789,987654321
POST_INTERVAL_HOURS=3
DATABASE_PATH=data/bot.db
PROXY_ENABLED=true
PROXY_URL=socks5h://127.0.0.1:1080
PROXY_CONNECT_TIMEOUT_SECONDS=30
BATCH_NOTIFICATION_ENABLED=true
BATCH_NOTIFICATION_DELAY_SECONDS=5
LOG_LEVEL=INFO
```

### `TARGET_CHANNEL_ID`

- Для публичного канала укажите `@username`.
- Для приватного канала укажите числовой ID вида `-1001234567890`.

### Прокси и sing-box

`PROXY_URL` поддерживает схемы `socks5://` и `socks5h://`. Для локального sing-box обычно подходит:

```env
PROXY_ENABLED=true
PROXY_URL=socks5h://127.0.0.1:1080
```

`aiogram` принимает SOCKS-прокси через `aiohttp-socks`; `socks5h://` сохраняется как исходная настройка и передаётся в сессию как совместимый `socks5://` URL.

## Локальный запуск

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m bot.main
```

## systemd

Unit-файл находится в `systemd/raccoon-channel-poster.service`. Он рассчитан на установку проекта в `/opt/raccoon-channel-poster` и запуск после `raccoon-sing-box.service`.

```bash
sudo cp systemd/raccoon-channel-poster.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now raccoon-channel-poster.service
journalctl -u raccoon-channel-poster.service -f
```

Если sing-box не используется, уберите из unit-файла строки `After=... raccoon-sing-box.service` и `Requires=raccoon-sing-box.service` либо оставьте только `After=network-online.target`.

## Команды администратора

- `/start` — краткая инструкция.
- `/help` — список команд.
- `/status` — состояние публикации, размер очереди, следующий запуск и последний успешный пост.
- `/queue` — размер очереди и примерный запас в днях.
- `/pause` — приостановить автопубликацию.
- `/resume` — возобновить автопубликацию.
- `/next` — немедленно опубликовать следующий элемент и пересчитать следующий автозапуск.
- `/skip` — пропустить следующий элемент очереди.
- `/clear confirm` — пометить текущую очередь как пропущенную.

## SQLite

Используются только две таблицы:

- `queue_items` — элементы очереди и история статусов.
- `bot_state` — служебные флаги (`paused`, `next_run_at`, `last_success_at`).

При инициализации база удаляет таблицы старого Telegram-бота, если они остались после миграции: `users`, `channels`, `posts`, `post_batches`, `channel_schedules`, `publish_logs`, `edit_logs`.

### Резервное копирование

```bash
sqlite3 data/bot.db ".backup 'backup/bot-$(date +%F).db'"
```

Восстановление:

```bash
sudo systemctl stop raccoon-channel-poster.service
cp backup/bot-YYYY-MM-DD.db data/bot.db
sudo systemctl start raccoon-channel-poster.service
```

## Проверка

```bash
pytest
python -m compileall bot tests
```
