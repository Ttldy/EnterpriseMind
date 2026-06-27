from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.evaluation.contracts import EvaluationCase

BenchmarkModule = Literal[
    "intent",
    "tools",
    "composite",
    "monitoring",
]


@dataclass(frozen=True)
class BenchmarkProfile:
    name: str
    settings: dict[str, str]

    @classmethod
    def baseline(cls) -> BenchmarkProfile:
        return cls(
            name="baseline",
            settings={
                "INTENT_ROUTER_MODE": "rule",
                "TOOL_MANAGER_ENABLED": "false",
                "COMPOSITE_AGENT_ENABLED": "false",
                "MONITOR_ENABLED": "false",
            },
        )

    @classmethod
    def enhanced(cls) -> BenchmarkProfile:
        return cls(
            name="enhanced",
            settings={
                "INTENT_ROUTER_MODE": "hybrid",
                "TOOL_MANAGER_ENABLED": "true",
                "COMPOSITE_AGENT_ENABLED": "true",
                "MONITOR_ENABLED": "true",
            },
        )


@dataclass(frozen=True)
class BenchmarkCase:
    evaluation: EvaluationCase
    benchmark_module: BenchmarkModule
    expected_intent: str | None = None
    expected_requires_sql: bool | None = None
    expected_sensitivity: str | None = None
    expected_tool_success: bool | None = None
    expected_tool_cache_hit: bool | None = None
    expected_tool_timeout: bool | None = None
    expected_tool_fallback: bool | None = None
    expected_tool_circuit_open: bool | None = None
    expected_permission_block: bool | None = None
    expected_unsafe_sql_block: bool | None = None
    expected_composite: bool | None = None
    expected_monitor_warning: bool | None = None
    notes: str | None = None


JsonDict = dict[str, Any]
