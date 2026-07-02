import asyncio

import pytest

from app.monitoring.contracts import MonitorEvent
from app.monitoring.service import MonitoringService


def event(operation: str = "run") -> MonitorEvent:
    return MonitorEvent(
        component="orchestrator",
        operation=operation,
        success=True,
        latency_ms=12,
    )


class RecordingWriter:
    def __init__(self, fail_first: bool = False) -> None:
        self.fail_first = fail_first
        self.calls = 0
        self.events: list[MonitorEvent] = []
        self.called = asyncio.Event()

    async def write(self, events: list[MonitorEvent]) -> None:
        self.calls += 1
        self.called.set()
        if self.fail_first and self.calls == 1:
            raise RuntimeError("database unavailable")
        self.events.extend(events)


def test_disabled_monitor_does_not_enqueue() -> None:
    service = MonitoringService(
        writer=RecordingWriter(),
        enabled=False,
        queue_max_size=1,
    )

    assert service.record(event()) is False
    assert service.queue_size == 0


def test_queue_full_drops_event_without_blocking() -> None:
    service = MonitoringService(
        writer=RecordingWriter(),
        enabled=True,
        queue_max_size=1,
    )

    assert service.record(event("first")) is True
    assert service.record(event("second")) is False
    assert service.queue_size == 1
    assert service.dropped_events == 1


@pytest.mark.asyncio
async def test_background_consumer_batches_and_flushes_on_stop() -> None:
    writer = RecordingWriter()
    service = MonitoringService(
        writer=writer,
        enabled=True,
        queue_max_size=10,
        batch_size=10,
        flush_interval_seconds=0.01,
    )
    await service.start()
    service.record(event("one"))
    service.record(event("two"))

    await asyncio.wait_for(writer.called.wait(), timeout=1)
    await service.stop(timeout_seconds=1)

    assert [item.operation for item in writer.events] == ["one", "two"]
    assert service.is_running is False


@pytest.mark.asyncio
async def test_consumer_continues_after_writer_failure() -> None:
    writer = RecordingWriter(fail_first=True)
    service = MonitoringService(
        writer=writer,
        enabled=True,
        queue_max_size=10,
        batch_size=1,
        flush_interval_seconds=0.01,
    )
    await service.start()
    service.record(event("failed-batch"))
    while writer.calls < 1:
        await asyncio.sleep(0.01)
    writer.called.clear()
    service.record(event("next-batch"))

    await asyncio.wait_for(writer.called.wait(), timeout=1)
    await service.stop(timeout_seconds=1)

    assert writer.calls >= 2
    assert [item.operation for item in writer.events] == ["next-batch"]

