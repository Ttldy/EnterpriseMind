import asyncio

import pytest

from app.monitoring.context import current_trace_id, trace_context


@pytest.mark.asyncio
async def test_trace_context_is_isolated_between_concurrent_tasks() -> None:
    entered = asyncio.Event()
    release = asyncio.Event()
    values: list[tuple[str, str | None]] = []

    async def worker(trace_id: str) -> None:
        with trace_context(trace_id):
            entered.set()
            await release.wait()
            values.append((trace_id, current_trace_id()))

    first = asyncio.create_task(worker("trace-a"))
    second = asyncio.create_task(worker("trace-b"))
    await entered.wait()
    release.set()
    await asyncio.gather(first, second)

    assert sorted(values) == [
        ("trace-a", "trace-a"),
        ("trace-b", "trace-b"),
    ]
    assert current_trace_id() is None

