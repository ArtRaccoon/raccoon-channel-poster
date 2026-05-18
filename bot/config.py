from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    bot_token: str
    admin_ids: list[int]
    proxy_url: str
    timezone: str
    data_dir: Path
    media_dir: Path
    log_level: str


def _parse_admin_ids(raw_value: str) -> list[int]:
    if not raw_value.strip():
        return []

    result: list[int] = []
    for chunk in raw_value.split(","):
        item = chunk.strip()
        if not item:
            continue
        try:
            result.append(int(item))
        except ValueError as exc:
            raise ValueError(f"Invalid ADMIN_IDS item: '{item}'") from exc
    return result


def load_settings() -> Settings:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))
    proxy_url = os.getenv("PROXY_URL", "").strip()
    timezone = os.getenv("TIMEZONE", "UTC").strip() or "UTC"
    data_dir = Path(os.getenv("DATA_DIR", "data")).resolve()
    media_dir = Path(os.getenv("MEDIA_DIR", str(data_dir / "media"))).resolve()
    log_level = os.getenv("LOG_LEVEL", "INFO").strip() or "INFO"

    if not bot_token:
        raise ValueError("BOT_TOKEN is required")

    return Settings(
        bot_token=bot_token,
        admin_ids=admin_ids,
        proxy_url=proxy_url,
        timezone=timezone,
        data_dir=data_dir,
        media_dir=media_dir,
        log_level=log_level,
    )
