# Raccoon Channel Poster

Минималистичный Telegram-бот автопубликации медиа в канал. Администратор отправляет боту фото, видео, GIF-анимации или изображения-документы; бот без подтверждений складывает каждое сообщение в FIFO-очередь и публикует по одному элементу каждые 3 часа.

## Возможности

- Новая SQLite-база: `data/autoposter.db`.
- Поддержка `photo`, `video`, `animation`, изображений как `document`.
- Массовая загрузка 100+ медиа без кнопок и предпросмотра.
- Агрегированное уведомление о пачке после короткой паузы.
- SOCKS5/SOCKS5H-прокси для всех запросов к Telegram.
- Переживает рестарт и возвращает `publishing` элементы в очередь.
- Не использует APScheduler.

## 1. Создание бота через BotFather

1. Откройте `@BotFather`.
2. Выполните `/newbot`.
3. Задайте имя и username.
4. Скопируйте токен в `.env` как `BOT_TOKEN`.

## 2. Права бота в канале

Добавьте бота администратором целевого канала и разрешите публикацию сообщений. Без прав администратора Telegram API вернёт ошибку отправки.

## 3. Получение `TARGET_CHANNEL_ID`

Можно использовать username канала:

```env
TARGET_CHANNEL_ID=@channel_name
```

Или числовой ID вида:

```env
TARGET_CHANNEL_ID=-1001234567890
```

## 4. Получение `ADMIN_IDS`

Напишите любому боту для получения Telegram user id, например `@userinfobot`, и укажите один или несколько ID через запятую:

```env
ADMIN_IDS=123456789,987654321
```

## 5. Настройка `.env`

```bash
cd /home/postingbot/bots/raccoon-channel-poster
cp .env.example .env
nano .env
```

Пример:

```env
BOT_TOKEN=123:secret
TARGET_CHANNEL_ID=@channel_name
ADMIN_IDS=123456789
POST_INTERVAL_HOURS=3
DATABASE_PATH=data/autoposter.db
TIMEZONE=Europe/Moscow
PROXY_ENABLED=true
PROXY_URL=socks5h://127.0.0.1:1080
PROXY_CONNECT_TIMEOUT_SECONDS=30
BATCH_NOTIFICATION_ENABLED=true
BATCH_NOTIFICATION_DELAY_SECONDS=5
LOG_LEVEL=INFO
```

## 6. Проверка sing-box

Прокси запускается отдельным сервисом `raccoon-sing-box.service`; бот его не запускает.

```bash
sudo systemctl status raccoon-sing-box.service --no-pager -l
```

## 7. Установка зависимостей

```bash
cd /home/postingbot/bots/raccoon-channel-poster
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 8. Первый запуск

```bash
cd /home/postingbot/bots/raccoon-channel-poster
source .venv/bin/activate
python -m bot.main
```

## 9. systemd

```bash
sudo cp systemd/raccoon-channel-poster.service /etc/systemd/system/raccoon-channel-poster.service
sudo systemctl daemon-reload
sudo systemctl enable --now raccoon-channel-poster.service
sudo systemctl status raccoon-channel-poster.service --no-pager -l
```

## 10. Команды бота

- `/start` — краткое описание.
- `/help` — список команд.
- `/status` — пауза, размер очереди, следующая публикация, последняя успешная публикация, последняя ошибка.
- `/queue` — количество элементов и примерный запас в днях.
- `/pause` — остановить только автопубликацию; приём медиа продолжается.
- `/resume` — возобновить автопубликацию.
- `/next` — немедленно опубликовать следующий элемент, работает даже на паузе.
- `/skip` — пометить первый queued-элемент как `skipped`.
- `/clear` — предупреждение.
- `/clear confirm` — пометить все `queued` и `publishing` элементы как `skipped`.

## 11. Резервное копирование новой базы

```bash
cd /home/postingbot/bots/raccoon-channel-poster
sqlite3 data/autoposter.db ".backup 'data/autoposter.backup.db'"
```

## 12. Восстановление

```bash
sudo systemctl stop raccoon-channel-poster.service
cd /home/postingbot/bots/raccoon-channel-poster
cp data/autoposter.backup.db data/autoposter.db
sudo systemctl start raccoon-channel-poster.service
```

Старый файл `data/bot.db` не используется новой версией.

## 13. Обновление проекта

```bash
cd /home/postingbot/bots/raccoon-channel-poster
git pull
source .venv/bin/activate
pip install -r requirements.txt
python -m compileall bot tests
python -m pytest -q
sudo systemctl daemon-reload
sudo systemctl restart raccoon-channel-poster.service
sudo systemctl status raccoon-channel-poster.service --no-pager -l
```
