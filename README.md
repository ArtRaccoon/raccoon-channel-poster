# Raccoon Channel Poster

Минималистичный Telegram-бот автопубликации медиа в канал. Администратор отправляет боту фото, видео, GIF-анимации или изображения-документы; бот складывает каждое сообщение в FIFO-очередь и публикует по одному элементу с заданным интервалом.

Канал больше не настраивается через `.env`: бот запускается без подключённого канала, хранит выбранный канал в SQLite и автоматически начинает публикацию после команды `/setchannel`.

## Возможности

- SQLite-база `data/autoposter.db` для очереди, состояния, канала, интервала публикации и блока ссылок.
- Поддержка `photo`, `video`, `animation`, изображений как `document`.
- Массовая загрузка 100+ медиа без кнопок и предпросмотра.
- Агрегированное уведомление о пачке после короткой паузы.
- SOCKS5/SOCKS5H-прокси для всех запросов к Telegram.
- Переживает рестарт и возвращает `publishing` элементы в очередь.
- Запускается без подключённого канала и ждёт настройки.
- Не использует APScheduler.

## Быстрая настройка

1. Создайте бота через `@BotFather` и получите токен.
2. Заполните `.env`: `BOT_TOKEN`, `ADMIN_IDS` и технические настройки.
3. Запустите сервис.
4. Добавьте бота администратором канала с правом публикации сообщений.
5. Напишите боту `/setchannel`.
6. Перешлите любое сообщение из канала или отправьте `@username` канала.

Ручная настройка ID канала в `.env` не требуется.

## 1. Создание бота через BotFather

1. Откройте `@BotFather`.
2. Выполните `/newbot`.
3. Задайте имя и username.
4. Скопируйте токен в `.env` как `BOT_TOKEN`.

## 2. Получение `ADMIN_IDS`

Напишите любому боту для получения Telegram user id, например `@userinfobot`, и укажите один или несколько ID через запятую:

```env
ADMIN_IDS=123456789,987654321
```

Бот отвечает на команды только этим пользователям.

## 3. Настройка `.env`

```bash
cd /home/postingbot/bots/raccoon-channel-poster
cp .env.example .env
nano .env
```

Пример:

```env
BOT_TOKEN=123:secret
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

## 4. Установка зависимостей

```bash
cd /home/postingbot/bots/raccoon-channel-poster
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 5. Проверка sing-box

Прокси запускается отдельным сервисом `raccoon-sing-box.service`; бот его не запускает.

```bash
sudo systemctl status raccoon-sing-box.service --no-pager -l
```

## 6. Первый запуск

```bash
cd /home/postingbot/bots/raccoon-channel-poster
source .venv/bin/activate
python -m bot.main
```

Если канал ещё не подключён, `/start` покажет инструкцию: добавьте бота администратором канала, затем используйте `/setchannel` и перешлите сообщение из канала или отправьте `@username`.

## 7. Подключение канала

1. Добавьте бота администратором канала.
2. Включите для бота право публикации сообщений.
3. В личном чате с ботом отправьте `/setchannel`.
4. Перешлите любое сообщение из канала **или** отправьте `@username` канала.

Бот проверит, что он администратор канала и имеет право `can_post_messages`. Если всё корректно, канал будет сохранён в SQLite. Перезапуск приложения не нужен.

Для замены канала повторите `/setchannel` и отправьте новый канал. Для удаления подключённого канала используйте `/removechannel`; очередь при этом не удаляется.

## 8. systemd

```bash
sudo cp systemd/raccoon-channel-poster.service /etc/systemd/system/raccoon-channel-poster.service
sudo systemctl daemon-reload
sudo systemctl enable --now raccoon-channel-poster.service
sudo systemctl status raccoon-channel-poster.service --no-pager -l
```

## 9. Команды бота

- `/start` — краткое описание или инструкция подключения канала.
- `/help` — список команд.
- `/channel` — название, username, ID канала, актуальный интервал публикации и размер очереди.
- `/setchannel` — подключить или заменить канал.
- `/removechannel` — удалить сохранённый канал, не трогая очередь.
- `/status` — пауза, размер очереди, следующая публикация, последняя успешная публикация, последняя ошибка.
- `/queue` — количество элементов и примерный запас в днях.
- `/pause` — остановить только автопубликацию; приём медиа продолжается.
- `/resume` — возобновить автопубликацию.
- `/next` — немедленно опубликовать следующий элемент, работает даже на паузе, если канал подключён.
- `/interval` — показать текущий интервал, следующую публикацию и быстрые варианты.
- `/setinterval <hours>` — задать интервал от 0.25 до 168 часов; поддерживается запятая, например `0,5`.
- `/links` — показать текущий блок ссылок и кнопки управления.
- `/setlinks` — перейти в режим ввода нового блока ссылок.
- `/resetlinks` — вернуть стандартный блок ссылок.
- `/skip` — пометить первый queued-элемент как `skipped`.
- `/clear` — предупреждение.
- `/clear confirm` — пометить все `queued` и `publishing` элементы как `skipped`.

## 10. Кнопочное меню

Для администраторов бот показывает Reply-клавиатуру после `/start`, `/help`, успешной настройки канала и основных действий управления. Кнопки полностью дублируют команды, поэтому можно пользоваться как текстовыми командами, так и меню:

- `📊 Статус` — то же, что `/status`.
- `📚 Очередь` — то же, что `/queue`.
- `▶️ Опубликовать сейчас` — то же, что `/next`; если канал не настроен, бот ответит `Канал пока не настроен.`
- `⏸ Пауза` — то же, что `/pause`.
- `▶️ Продолжить` — то же, что `/resume`.
- `⏱ Интервал` — то же, что `/interval`; показывает быстрые кнопки `30 мин`, `1 ч`, `2 ч`, `3 ч`, `6 ч`, `12 ч`, `24 ч`.
- `🔗 Ссылки` — то же, что `/links`; позволяет изменить или сбросить блок ссылок.
- `⚙️ Канал` — то же, что `/channel`; если канал не настроен, бот ответит `Канал пока не настроен.`
- `🔗 Настроить канал` — то же, что `/setchannel`.
- `🗑 Очистить очередь` — показывает подтверждение `✅ Да, очистить очередь` / `❌ Отмена`; очередь не очищается без подтверждения.
- `❓ Помощь` — то же, что `/help`.

Меню доступно только пользователям из `ADMIN_IDS`; остальные получают прежний ответ `Нет доступа.`


## 11. Управление интервалом

Интервал автопубликации хранится в SQLite в `bot_settings.post_interval_hours` и меняется без перезапуска бота. Значение `POST_INTERVAL_HOURS` из `.env` больше не является единственным источником настройки: оно используется как default при первом запуске или если в базе ещё нет сохранённого значения.

Через Telegram доступны:

- `/interval` или кнопка `⏱ Интервал` — показать текущий интервал, следующую публикацию и быстрые варианты.
- Быстрые кнопки: `30 мин`, `1 ч`, `2 ч`, `3 ч`, `6 ч`, `12 ч`, `24 ч`.
- `/setinterval <hours>` — ручной ввод часов от `0.25` до `168`; можно писать `0,5`.

После изменения интервала бот пересчитывает `next_run_at = now + interval`. После успешной автопубликации и после `/next` при включённой автопубликации следующий запуск также считается по актуальному значению из SQLite.

## 12. Управление ссылками

Блок ссылок хранится в SQLite в `bot_settings.links_block` и подставляется в caption при публикации. Фиксированный блок из `bot/captions.py` теперь является `DEFAULT_LINKS_BLOCK`: он используется как default, если в базе нет пользовательского значения.

Через Telegram доступны:

- `/links` или кнопка `🔗 Ссылки` — показать текущий блок ссылок.
- `/setlinks` или `✏️ Изменить ссылки` — отправить новый блок ссылок следующим сообщением.
- `/resetlinks` или `🧹 Сбросить ссылки` — вернуться к стандартному блоку из `bot/captions.py`.
- `/cancel` или `⬅️ Назад` — отменить ввод ссылок.

Для блока ссылок разрешён HTML. Если админ отправляет сообщение с Telegram entities, бот сохраняет HTML-представление, чтобы ссылки продолжали работать. Пользовательская подпись медиа по-прежнему HTML-экранируется.

Ограничение Telegram на caption — 1024 символа. Блок ссылок ограничен 900 символами, потому что он должен помещаться в итоговый caption вместе с подписью пользователя и разделителем.

## 13. Default values

- `POST_INTERVAL_HOURS` из `.env` — default для интервала, пока в SQLite нет `post_interval_hours`.
- `DEFAULT_LINKS_BLOCK` из `bot/captions.py` — default для блока ссылок, пока в SQLite нет `links_block` или после сброса `/resetlinks`.

## 14. Резервное копирование базы

```bash
cd /home/postingbot/bots/raccoon-channel-poster
sqlite3 data/autoposter.db ".backup 'data/autoposter.backup.db'"
```

## 15. Восстановление

```bash
sudo systemctl stop raccoon-channel-poster.service
cd /home/postingbot/bots/raccoon-channel-poster
cp data/autoposter.backup.db data/autoposter.db
sudo systemctl start raccoon-channel-poster.service
```

## 16. Обновление проекта

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
