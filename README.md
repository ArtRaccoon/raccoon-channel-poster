# raccoon-channel-poster

Минимальный рабочий каркас Telegram-бота для создания, предпросмотра и публикации постов в Telegram-каналы.

## Что уже реализовано (v1)

- Проверка доступа по `ADMIN_IDS`.
- Команда `/start` с главным меню.
- Раздел `Настройки` c пунктами:
  - Добавить канал (заглушка)
  - Список каналов
  - Прокси-статус
  - Назад
- JSON-хранилище (`channels.json`, `drafts.json`, `posts.json`) с автосозданием файлов.
- Базовая статистика по количеству каналов, черновиков и постов.
- Логирование в `logs/bot.log`.
- Поддержка подключения через прокси (`PROXY_URL`) или прямого режима.

## Установка зависимостей

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Пример `.env`

Скопируйте `.env.example` в `.env` и заполните значения:

```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789
PROXY_URL=
TIMEZONE=UTC
DATA_DIR=data
MEDIA_DIR=data/media
LOG_LEVEL=INFO
```

## Запуск через `run.sh`

```bash
chmod +x run.sh
./run.sh
```

## Ручной запуск

```bash
python -m bot.main
```

## Важно

- Файл `.env` содержит секреты и **не должен коммититься**.
- В репозиторий нельзя добавлять реальные токены, ID каналов и адреса прокси.
