import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.monitoring.context import current_trace_id, trace_context
from app.monitoring.contracts import MonitorEvent
from app.monitoring.instrumentation import OperationTimer
from app.shared.trace import TraceIdMiddleware


class RecordingMonitor:
    def __init__(self) -> None:
        self.events: list[MonitorEvent] = []

    def record(self, event: MonitorEvent) -> bool:
        self.events.append(event)
        return True


@pytest.mark.asyncio
async def test_operation_timer_uses_real_elapsed_time_and_trace_context() -> None:
    monitor = RecordingMonitor()
    with trace_context("trace-real"):
        timer = OperationTimer(
            monitor,
            component="retrieval",
            operation="retrieve",
        )
        await asyncio.sleep(0.01)
        timer.finish(success=True, metadata={"query_count": 2})

    assert len(monitor.events) == 1
    saved = monitor.events[0]
    assert saved.trace_id == "trace-real"
    assert saved.latency_ms >= 5
    assert saved.metadata == {"query_count": 2}


def test_trace_middleware_sets_and_resets_monitor_context() -> None:
    app = FastAPI()
    app.add_middleware(TraceIdMiddleware)

    @app.get("/trace")
    async def read_trace() -> dict[str, str | None]:
        return {"trace_id": current_trace_id()}

    response = TestClient(app).get("/trace")

    assert response.status_code == 200
    assert response.json()["trace_id"] == response.headers["X-Trace-ID"]
    assert current_trace_id() is None

