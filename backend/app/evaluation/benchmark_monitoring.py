from datetime import UTC, datetime

from app.evaluation.benchmark_contracts import BenchmarkCase, BenchmarkProfile
from app.monitoring.contracts import MonitorEvent
from app.monitoring.scoring import HealthScorer, HealthStatus


class ControlledMonitoringFixture:
    """Build deterministic events from case fields, never question text."""

    def __init__(self, latency_warning_ms: int = 2000) -> None:
        self._scorer = HealthScorer(latency_warning_ms)

    def metadata(
        self, case: BenchmarkCase, profile: BenchmarkProfile
    ) -> dict[str, object]:
        if case.benchmark_module not in {"monitoring", "tools"}:
            return {}
        if profile.settings.get("MONITOR_ENABLED") != "true":
            return {
                **self._summary([]),
                "tool_success": False,
                "tool_cache_hit": False,
                "tool_timeout": False,
                "tool_fallback": False,
                "tool_circuit_open": False,
            }
        timeout = case.expected_tool_timeout is True
        fallback = case.expected_tool_fallback is True
        circuit_open = case.expected_tool_circuit_open is True
        success = (
            case.expected_tool_success
            if case.expected_tool_success is not None
            else not (timeout or circuit_open)
        )
        business_outcome = (
            case.evaluation.category == "safety" and not success
        )
        event = MonitorEvent(
            trace_id=f"benchmark-{case.evaluation.case_id}",
            component="tool_manager",
            operation="controlled_fixture",
            success=success,
            latency_ms=3000 if timeout else 100,
            error_code=(
                "tool_timeout"
                if timeout
                else "circuit_open"
                if circuit_open
                else "unsafe_sql_rejected"
                if business_outcome
                else None
            ),
            agent=case.evaluation.expected_agent,
            provider=None,
            model=None,
            timeout=timeout,
            cache_hit=False,
            fallback=fallback,
            circuit_open=circuit_open,
            created_at=datetime.now(UTC),
            metadata={"business_outcome": business_outcome},
        )
        return {
            **self._summary([event]),
            "tool_success": success,
            "tool_cache_hit": case.expected_tool_cache_hit is True,
            "tool_timeout": timeout,
            "tool_fallback": fallback,
            "tool_circuit_open": circuit_open,
        }

    def _summary(self, events: list[MonitorEvent]) -> dict[str, object]:
        result = self._scorer.score(
            events, component="overall", window_minutes=5
        )
        score = result.health_score
        return {
            "monitor_warning_detected": result.status
            in {HealthStatus.WARNING, HealthStatus.DEGRADED},
            "monitor_penalty_delta": 0.0 if score is None else 1.0 - score,
            "tool_timeout_count": sum(event.timeout for event in events),
            "tool_fallback_count": sum(event.fallback for event in events),
            "tool_circuit_open_count": sum(
                event.circuit_open for event in events
            ),
            "monitor_fixture_source": "controlled_event",
        }
