from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentHealth:
    component: str
    success_rate: float
    average_latency_ms: float
    health_score: float
    monitor_penalty: float
    warning: bool
    reason: str


class MonitoringService:
    def __init__(
        self,
        latency_warning_ms: int = 2000,
    ) -> None:
        self._latency_warning_ms = latency_warning_ms
        self._events: dict[str, list[tuple[bool, int]]] = {}

    def record(
        self,
        component: str,
        success: bool,
        latency_ms: int,
    ) -> ComponentHealth:
        values = self._events.setdefault(
            component,
            [],
        )
        values.append((success, latency_ms))
        return self.health(component)

    def health(
        self,
        component: str,
    ) -> ComponentHealth:
        values = self._events.get(component, [])
        if not values:
            return ComponentHealth(
                component=component,
                success_rate=1.0,
                average_latency_ms=0.0,
                health_score=1.0,
                monitor_penalty=0.0,
                warning=False,
                reason="healthy",
            )

        success_rate = sum(1 for success, _ in values if success) / len(values)
        average_latency = sum(latency for _, latency in values) / len(values)
        latency_penalty = min(
            0.5,
            average_latency / max(self._latency_warning_ms, 1) * 0.25,
        )
        failure_penalty = (1.0 - success_rate) * 0.6
        penalty = min(
            1.0,
            failure_penalty + latency_penalty,
        )
        warning = (
            success_rate < 1.0
            or average_latency >= self._latency_warning_ms
        )
        reason = (
            "failure_or_latency_warning"
            if warning
            else "healthy"
        )
        return ComponentHealth(
            component=component,
            success_rate=success_rate,
            average_latency_ms=average_latency,
            health_score=max(0.0, 1.0 - penalty),
            monitor_penalty=penalty,
            warning=warning,
            reason=reason,
        )

    def evaluate_question(
        self,
        question: str,
    ) -> ComponentHealth:
        normalized = question.lower()
        if "超时" in normalized or "timeout" in normalized:
            return ComponentHealth(
                component="simulated_tool",
                success_rate=0.0,
                average_latency_ms=float(self._latency_warning_ms),
                health_score=0.35,
                monitor_penalty=0.65,
                warning=True,
                reason="simulated_timeout",
            )
        if (
            "circuit open" in normalized
            or "连续失败" in normalized
            or "熔断" in normalized
        ):
            return ComponentHealth(
                component="simulated_tool",
                success_rate=0.0,
                average_latency_ms=0.0,
                health_score=0.25,
                monitor_penalty=0.75,
                warning=True,
                reason="simulated_circuit_open",
            )
        return ComponentHealth(
            component="question",
            success_rate=1.0,
            average_latency_ms=0.0,
            health_score=1.0,
            monitor_penalty=0.0,
            warning=False,
            reason="healthy",
        )
