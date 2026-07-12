from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

MEDIA_TYPES = {"photo", "video", "animation", "document"}
QUEUED = "queued"
PUBLISHING = "publishing"
PUBLISHED = "published"
FAILED = "failed"
SKIPPED = "skipped"


@dataclass(frozen=True)
class QueueItem:
    id: int
    source_chat_id: int
    source_message_id: int
    media_group_id: str | None
    media_type: str
    file_id: str
    caption: str | None
    status: str
    attempts: int
    last_error: str | None
    created_at: str
    published_at: str | None
