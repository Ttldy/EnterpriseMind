from datetime import UTC, datetime, timedelta

import pytest

from app.monitoring.contracts import MonitorEvent
from app.monitoring.scoring import HealthScorer, HealthStatus

NOW = datetime(2026, 7, 2, 4, 0, tzinfo=UTC)


def event(
    *,
    component: str = "tool_manager",
    success: bool = True,
    latency_ms: int = 100,
    timeout: bool = False,
    fallback: bool = False,
    circuit_open: bool = False,
    error_code: str | None = None,
    created_at: datetime = NOW,
    metadata: dict[str, object] | None = None,
) -> MonitorEvent:
    return MonitorEvent(
        component=component,
        operation="knowledge_search",
        success=success,
        latency_ms=latency_ms,
        timeout=timeout,
        fallback=fallback,
        circuit_open=circuit_open,
        error_code=error_code,
        created_at=created_at,
        metadata=metadata or {},
    )


def test_no_events_returns_no_data_instead_of_perfect_health() -> None:
    result = HealthScorer(latency_warning_ms=2000).score(
        [],
        component="overall",
        window_minutes=5,
        now=NOW,
    )

    assert result.status is HealthStatus.NO_DATA
    assert result.health_score is None
    assert result.event_count == 0


def test_all_success_low_latency_is_healthy() -> None:
    result = HealthScorer(latency_warning_ms=2000).score(
        [event(latency_ms=100), event(latency_ms=200)],
        component="tool_manager",
        window_minutes=5,
        now=NOW,
    )

    assert result.status is HealthStatus.HEALTHY
    assert result.health_score == pytest.approx(1.0)
    assert result.success_rate == pytest.approx(1.0)
    assert result.p95_latency_ms == 200


def test_each_real_failure_signal_adds_its_penalty() -> None:
    result = HealthScorer(latency_warning_ms=100).score(
        [
            event(
                success=False,
                latency_ms=200,
                timeout=True,
                fallback=True,
                circuit_open=True,
                error_code="timeout",
            )
        ],
        component="tool_manager",
        window_minutes=5,
        now=NOW,
    )

    assert result.health_score == pytest.approx(0.0)
    assert result.status is HealthStatus.DEGRADED
    assert result.penalties == {
        "failure": pytest.approx(0.4),
        "timeout": pytest.approx(0.2),
        "latency": pytest.approx(0.2),
        "fallback": pytest.approx(0.1),
        "circuit_open": pytest.approx(0.1),
    }


def test_old_events_do_not_participate_in_window() -> None:
    old = event(
        success=False,
        latency_ms=5000,
        created_at=NOW - timedelta(minutes=6),
    )
    current = event()

    result = HealthScorer(latency_warning_ms=2000).score(
        [old, current],
        component="tool_manager",
        window_minutes=5,
        now=NOW,
    )

    assert result.event_count == 1
    assert result.health_score == pytest.approx(1.0)


@pytest.mark.parametrize(
    "error_code",
    [
        "evidence_insufficient",
        "permission_denied",
        "unsafe_sql_rejected",
    ],
)
def test_expected_security_outcomes_are_not_technical_failures(
    error_code: str,
) -> None:
    result = HealthScorer(latency_warning_ms=2000).score(
        [
            event(
                component="orchestrator",
                success=False,
                error_code=error_code,
                metadata={"business_outcome": error_code},
            )
        ],
        component="orchestrator",
        window_minutes=5,
        now=NOW,
    )

    assert result.success_rate == pytest.approx(1.0)
    assert result.health_score == pytest.approx(1.0)
    assert result.status is HealthStatus.HEALTHY
