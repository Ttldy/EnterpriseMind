import asyncio

import pytest

from app.monitoring.contracts import MonitorEvent
from app.tools.contracts import ToolContext, ToolSpec
from app.tools.manager import EnterpriseToolManager


class RecordingMonitor:
    def __init__(self) -> None:
        self.events: list[MonitorEvent] = []

    def record(self, event: MonitorEvent) -> bool:
        self.events.append(event)
        return True


class CacheableTool:
    spec = ToolSpec(
        name="cacheable",
        description="cacheable",
        input_schema={"type": "object"},
        cache_enabled=True,
        cache_ttl_seconds=30,
    )

    async def run(self, payload, context):
        del payload, context
        return {"ok": True}


class TimeoutTool:
    spec = ToolSpec(
        name="timeout_tool",
        description="timeout",
        input_schema={"type": "object"},
        timeout_ms=1,
    )

    async def run(self, payload, context):
        del payload, context
        await asyncio.sleep(0.05)
        return {"ok": True}


@pytest.mark.asyncio
async def test_tool_manager_records_success_cache_hit_and_trace() -> None:
    monitor = RecordingMonitor()
    manager = EnterpriseToolManager(monitor=monitor)
    manager.register(CacheableTool())
    context = ToolContext(user_id=1, trace_id="tool-trace")

    await manager.execute("cacheable", {}, context)
    await manager.execute("cacheable", {}, context)

    assert len(monitor.events) == 2
    assert monitor.events[0].success is True
    assert monitor.events[0].cache_hit is False
    assert monitor.events[1].cache_hit is True
    assert monitor.events[1].trace_id == "tool-trace"


@pytest.mark.asyncio
async def test_tool_manager_records_real_timeout() -> None:
    monitor = RecordingMonitor()
    manager = EnterpriseToolManager(monitor=monitor)
    manager.register(TimeoutTool())

    result = await manager.execute(
        "timeout_tool",
        {},
        ToolContext(user_id=1),
    )

    assert result.error_code == "timeout"
    assert monitor.events[0].success is False
    assert monitor.events[0].timeout is True
    assert monitor.events[0].error_code == "timeout"
    assert monitor.events[0].latency_ms >= 0

