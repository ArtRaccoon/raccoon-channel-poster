from __future__ import annotations

import os
from dataclasses import dataclass

def load_env(path: str = ".env") -> None:
    env_path = os.fspath(path)
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_env()


def _parse_ids(raw: str) -> list[int]:
    return [int(value.strip()) for value in raw.replace(';', ',').split(',') if value.strip()]


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


@dataclass(slots=True)
class Config:
    bot_token: str
    target_channel_id: str
    admin_ids: list[int]
    post_interval_hours: float
    database_path: str
    proxy_enabled: bool
    proxy_url: str
    proxy_connect_timeout_seconds: int
    batch_notification_enabled: bool
    batch_notification_delay_seconds: float
    log_level: str

    @property
    def post_interval_seconds(self) -> float:
        return self.post_interval_hours * 3600


def load_config() -> Config:
    return Config(
        bot_token=os.getenv('BOT_TOKEN', ''),
        target_channel_id=os.getenv('TARGET_CHANNEL_ID', ''),
        admin_ids=_parse_ids(os.getenv('ADMIN_IDS', '')),
        post_interval_hours=float(os.getenv('POST_INTERVAL_HOURS', '3')),
        database_path=os.getenv('DATABASE_PATH', 'data/bot.db'),
        proxy_enabled=_bool('PROXY_ENABLED', False),
        proxy_url=os.getenv('PROXY_URL', 'socks5h://127.0.0.1:1080'),
        proxy_connect_timeout_seconds=int(os.getenv('PROXY_CONNECT_TIMEOUT_SECONDS', '30')),
        batch_notification_enabled=_bool('BATCH_NOTIFICATION_ENABLED', True),
        batch_notification_delay_seconds=float(os.getenv('BATCH_NOTIFICATION_DELAY_SECONDS', '5')),
        log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
    )
