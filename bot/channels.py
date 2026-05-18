from __future__ import annotations

from bot.storage import JsonStorage


def get_channels(storage: JsonStorage) -> list[dict]:
    return storage.read_list(storage.channels_path)
