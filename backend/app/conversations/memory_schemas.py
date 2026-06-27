from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class MemoryRecord:
    user_id: int
    department: str
    roles: tuple[str, ...]
    conversation_id: int
    message_ids: tuple[int, ...]
    memory_type: str
    sensitivity: str
    text: str
    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )
    share_scope: str = "private"


@dataclass(frozen=True)
class MemorySearchHit:
    text: str
    score: float
    memory_type: str
    sensitivity: str
