from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class JsonStorage:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.channels_path = data_dir / "channels.json"
        self.drafts_path = data_dir / "drafts.json"
        self.posts_path = data_dir / "posts.json"

    def ensure_files(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        for path in (self.channels_path, self.drafts_path, self.posts_path):
            self._ensure_file(path)

    def _ensure_file(self, path: Path) -> None:
        if path.exists():
            return
        path.write_text("[]", encoding="utf-8")

    def read_list(self, path: Path) -> list[dict[str, Any]]:
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, list):
                raise ValueError(f"JSON in {path} is not a list")
            return data
        except json.JSONDecodeError as exc:
            logger.error("JSON decode error in %s: %s", path, exc)
            raise RuntimeError(f"JSON file is corrupted: {path}") from exc
        except FileNotFoundError as exc:
            logger.error("JSON file not found: %s", path)
            raise RuntimeError(f"JSON file not found: {path}") from exc

    def count_all(self) -> dict[str, int]:
        return {
            "channels": len(self.read_list(self.channels_path)),
            "drafts": len(self.read_list(self.drafts_path)),
            "posts": len(self.read_list(self.posts_path)),
        }
