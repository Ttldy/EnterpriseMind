from datetime import UTC, datetime

from app.monitoring.contracts import MonitorEvent
from app.monitoring.service import MonitoringService


def _event() -> MonitorEvent:
    return MonitorEvent(
        trace_id="trace-real",
        component="orchestrator",
        operation="run",
        success=True,
        latency_ms=7,
        error_code=None,
        agent="it",
        provider=None,
        model=None,
        timeout=False,
        cache_hit=False,
        fallback=False,
        circuit_open=False,
        created_at=datetime.now(UTC),
        metadata={},
    )


def test_disabled_monitor_does_not_collect() -> None:
    service = MonitoringService(enabled=False)
    assert service.record(_event()) is False
    assert service.queue_size == 0


def test_user_text_cannot_trigger_simulated_monitoring() -> None:
    service = MonitoringService()
    assert not hasattr(service, "evaluate_question")
    assert service.queue_size == 0
