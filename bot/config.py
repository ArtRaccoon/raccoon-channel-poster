from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    pass


def _bool(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_admin_ids(raw: str) -> set[int]:
    ids: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError as exc:
            raise ConfigError(f"ADMIN_IDS contains non-numeric value: {part!r}") from exc
    if not ids:
        raise ConfigError("ADMIN_IDS must contain at least one Telegram user id")
    return ids



@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: set[int]
    post_interval_hours: float = 3
    database_path: str = "data/autoposter.db"
    timezone: str = "Europe/Moscow"
    proxy_enabled: bool = True
    proxy_url: str = "socks5h://127.0.0.1:1080"
    proxy_connect_timeout_seconds: float = 30
    batch_notification_enabled: bool = True
    batch_notification_delay_seconds: float = 5
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, env_file: str | os.PathLike[str] | None = ".env") -> Self:
        if env_file:
            load_dotenv(env_file)
        token = os.getenv("BOT_TOKEN", "").strip()
        admins = os.getenv("ADMIN_IDS", "").strip()
        missing = [name for name, value in (("BOT_TOKEN", token), ("ADMIN_IDS", admins)) if not value]
        if missing:
            raise ConfigError("Missing required environment variables: " + ", ".join(missing))
        proxy_enabled = _bool(os.getenv("PROXY_ENABLED"), True)
        proxy_url = os.getenv("PROXY_URL", "socks5h://127.0.0.1:1080").strip()
        if proxy_enabled and not (proxy_url.startswith("socks5://") or proxy_url.startswith("socks5h://")):
            raise ConfigError("PROXY_URL must start with socks5:// or socks5h://")
        db_path = os.getenv("DATABASE_PATH", "data/autoposter.db").strip() or "data/autoposter.db"
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        return cls(
            bot_token=token,
            admin_ids=parse_admin_ids(admins),
            post_interval_hours=float(os.getenv("POST_INTERVAL_HOURS", "3")),
            database_path=db_path,
            timezone=os.getenv("TIMEZONE", "Europe/Moscow").strip() or "Europe/Moscow",
            proxy_enabled=proxy_enabled,
            proxy_url=proxy_url,
            proxy_connect_timeout_seconds=float(os.getenv("PROXY_CONNECT_TIMEOUT_SECONDS", "30")),
            batch_notification_enabled=_bool(os.getenv("BATCH_NOTIFICATION_ENABLED"), True),
            batch_notification_delay_seconds=float(os.getenv("BATCH_NOTIFICATION_DELAY_SECONDS", "5")),
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO",
        )
