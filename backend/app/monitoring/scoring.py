from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from app.monitoring.contracts import MonitorEvent


class HealthStatus(StrEnum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    NO_DATA = "NO_DATA"


@dataclass(frozen=True)
class HealthMetrics:
    component: str
    event_count: int
    success_rate: float
    average_latency_ms: float
    p95_latency_ms: int
    timeout_rate: float
    fallback_rate: float
    circuit_open_rate: float
    health_score: float | None
    status: HealthStatus
    reasons: tuple[str, ...] = ()
    penalties: dict[str, float] = field(
        default_factory=dict
    )


BUSINESS_OUTCOME_CODES = frozenset(
    {
        "evidence_insufficient",
        "permission_denied",
        "unsafe_sql_rejected",
    }
)


class HealthScorer:
    def __init__(self, latency_warning_ms: int) -> None:
        self._latency_warning_ms = max(1, latency_warning_ms)

    def score(
        self,
        events: list[MonitorEvent],
        *,
        component: str,
        window_minutes: int,
        now: datetime | None = None,
    ) -> HealthMetrics:
        current = now or datetime.now(UTC)
        cutoff = current - timedelta(
            minutes=max(1, window_minutes)
        )
        values = [
            event
            for event in events
            if event.created_at >= cutoff
            and (
                component == "overall"
                or event.component == component
            )
        ]
        if not values:
            return HealthMetrics(
                component=component,
                event_count=0,
                success_rate=0.0,
                average_latency_ms=0.0,
                p95_latency_ms=0,
                timeout_rate=0.0,
                fallback_rate=0.0,
                circuit_open_rate=0.0,
                health_score=None,
                status=HealthStatus.NO_DATA,
                reasons=("窗口内没有监控事件",),
                penalties=_empty_penalties(),
            )

        count = len(values)
        technical_failures = sum(
            1
            for event in values
            if not event.success
            and event.error_code not in BUSINESS_OUTCOME_CODES
            and not event.metadata.get("business_outcome")
        )
        success_rate = 1.0 - technical_failures / count
        timeout_rate = sum(event.timeout for event in values) / count
        fallback_rate = sum(event.fallback for event in values) / count
        circuit_rate = sum(event.circuit_open for event in values) / count
        latencies = sorted(event.latency_ms for event in values)
        average_latency = sum(latencies) / count
        p95 = latencies[
            max(0, math.ceil(count * 0.95) - 1)
        ]

        penalties = {
            "failure": (1.0 - success_rate) * 0.40,
            "timeout": timeout_rate * 0.20,
            "latency": self._latency_penalty(p95),
            "fallback": fallback_rate * 0.10,
            "circuit_open": circuit_rate * 0.10,
        }
        health_score = max(
            0.0,
            min(1.0, 1.0 - sum(penalties.values())),
        )
        status = (
            HealthStatus.HEALTHY
            if health_score >= 0.85
            else HealthStatus.WARNING
            if health_score >= 0.65
            else HealthStatus.DEGRADED
        )
        reasons = tuple(
            label
            for key, label in (
                ("failure", "技术失败率产生惩罚"),
                ("timeout", "超时率产生惩罚"),
                ("latency", "P95 延迟超过阈值"),
                ("fallback", "降级率产生惩罚"),
                ("circuit_open", "熔断率产生惩罚"),
            )
            if penalties[key] > 0
        ) or ("窗口内技术指标正常",)

        return HealthMetrics(
            component=component,
            event_count=count,
            success_rate=success_rate,
            average_latency_ms=average_latency,
            p95_latency_ms=p95,
            timeout_rate=timeout_rate,
            fallback_rate=fallback_rate,
            circuit_open_rate=circuit_rate,
            health_score=health_score,
            status=status,
            reasons=reasons,
            penalties=penalties,
        )

    def _latency_penalty(self, p95_latency_ms: int) -> float:
        if p95_latency_ms <= self._latency_warning_ms:
            return 0.0
        normalized = (
            p95_latency_ms / self._latency_warning_ms
        ) - 1.0
        return min(1.0, normalized) * 0.20


def _empty_penalties() -> dict[str, float]:
    return {
        "failure": 0.0,
        "timeout": 0.0,
        "latency": 0.0,
        "fallback": 0.0,
        "circuit_open": 0.0,
    }

