from dataclasses import dataclass
import os
from typing import List

from dotenv import load_dotenv


load_dotenv()


def _parse_owner_ids(raw: str) -> List[int]:
    if not raw.strip():
        return []
    return [int(item.strip()) for item in raw.split(',') if item.strip()]


@dataclass(slots=True)
class Config:
    bot_token: str
    owner_ids: List[int]
    proxy_url: str
    timezone: str
    database_path: str
    log_level: str

    @property
    def has_proxy(self) -> bool:
        return bool(self.proxy_url.strip())



def load_config() -> Config:
    return Config(
        bot_token=os.getenv('BOT_TOKEN', ''),
        owner_ids=_parse_owner_ids(os.getenv('OWNER_IDS', '')),
        proxy_url=os.getenv('PROXY_URL', ''),
        timezone=os.getenv('TIMEZONE', 'Europe/Moscow'),
        database_path=os.getenv('DATABASE_PATH', 'data/bot.db'),
        log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
    )
