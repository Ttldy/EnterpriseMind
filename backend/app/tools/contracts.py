from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.agents.contracts import Sensitivity


class ToolExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, object] = field(
        default_factory=dict
    )
    timeout_ms: int = 3000
    cache_ttl_seconds: int = 0
    cache_enabled: bool = False
    circuit_breaker_enabled: bool = True
    fallback_enabled: bool = True
    required_roles: frozenset[str] = frozenset()
    sensitivity: Sensitivity = Sensitivity.INTERNAL


@dataclass(frozen=True)
class ToolContext:
    user_id: int
    department: str | None = None
    roles: frozenset[str] = frozenset()
    trace_id: str | None = None
    request_id: str | None = None


@dataclass(frozen=True)
class ToolResult:
    success: bool
    output: object | None
    metadata: dict[str, object] = field(
        default_factory=dict
    )
    error: ToolExecutionError | None = None
    error_code: str | None = None
    error_message: str | None = None
    latency_ms: int = 0
    cache_hit: bool = False
    circuit_open: bool = False
    fallback_used: bool = False
    sensitivity: Sensitivity = Sensitivity.INTERNAL


class EnterpriseTool(Protocol):
    spec: ToolSpec

    async def run(
        self,
        payload: dict[str, object],
        context: ToolContext,
    ) -> object: ...
