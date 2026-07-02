from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

ALLOWED_METADATA_KEYS = frozenset(
    {
        "query_count",
        "successful_query_count",
        "failed_query_count",
        "citation_count",
        "evidence_level",
        "sensitivity",
        "external_sent",
        "refused",
        "row_count",
        "skipped",
        "skip_reason",
        "business_outcome",
        "tool_name",
        "subtask_count",
        "partial_success",
    }
)


def sanitize_metadata(
    metadata: dict[str, object],
) -> dict[str, object]:
    sanitized: dict[str, object] = {}
    for key, value in metadata.items():
        if key not in ALLOWED_METADATA_KEYS:
            continue
        if isinstance(value, bool | int | float):
            sanitized[key] = value
        elif isinstance(value, str):
            sanitized[key] = value[:120]
    return sanitized


@dataclass(frozen=True)
class MonitorEvent:
    component: str
    operation: str
    success: bool
    latency_ms: int
    trace_id: str | None = None
    error_code: str | None = None
    agent: str | None = None
    provider: str | None = None
    model: str | None = None
    timeout: bool = False
    cache_hit: bool = False
    fallback: bool = False
    circuit_open: bool = False
    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )
    metadata: dict[str, object] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "latency_ms",
            max(0, int(self.latency_ms)),
        )
        object.__setattr__(
            self,
            "metadata",
            sanitize_metadata(self.metadata),
        )


class MonitorRecorder(Protocol):
    def record(self, event: MonitorEvent) -> bool: ...

