from __future__ import annotations

from dataclasses import dataclass
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


def _parse_ids(raw: str) -> List[int]:
    return [int(x.strip()) for x in raw.replace(';', ',').split(',') if x.strip()]


def _bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {'1', 'true', 'yes', 'on'}


@dataclass(slots=True)
class Config:
    bot_token: str
    target_channel_id: str
    admin_ids: List[int]
    post_interval_hours: float
    database_path: str
    timezone: str
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
        admin_ids=_parse_ids(os.getenv('ADMIN_IDS', os.getenv('OWNER_IDS', ''))),
        post_interval_hours=float(os.getenv('POST_INTERVAL_HOURS', '3')),
        database_path=os.getenv('DATABASE_PATH', 'data/bot.db'),
        timezone=os.getenv('TIMEZONE', 'Europe/Moscow'),
        proxy_enabled=_bool('PROXY_ENABLED', False),
        proxy_url=os.getenv('PROXY_URL', 'socks5h://127.0.0.1:1080'),
        proxy_connect_timeout_seconds=int(os.getenv('PROXY_CONNECT_TIMEOUT_SECONDS', '30')),
        batch_notification_enabled=_bool('BATCH_NOTIFICATION_ENABLED', True),
        batch_notification_delay_seconds=float(os.getenv('BATCH_NOTIFICATION_DELAY_SECONDS', '5')),
        log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
    )
