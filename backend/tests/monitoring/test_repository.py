from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.monitoring.contracts import MonitorEvent
from app.monitoring.models import MonitorEventRecord
from app.monitoring.repository import PostgresMonitorWriter


@pytest.mark.asyncio
async def test_postgres_writer_uses_session_factory_and_persists_batch(
    session_factory,
) -> None:
    writer = PostgresMonitorWriter(session_factory)
    created_at = datetime(2026, 7, 2, 4, 0, tzinfo=UTC)

    await writer.write(
        [
            MonitorEvent(
                trace_id="trace-1",
                component="model_gateway",
                operation="generate",
                success=False,
                latency_ms=321,
                error_code="timeout",
                provider="ollama",
                model="qwen2.5:3b",
                timeout=True,
                fallback=True,
                created_at=created_at,
                metadata={
                    "sensitivity": "internal",
                    "question": "must not persist",
                },
            )
        ]
    )

    async with session_factory() as session:
        saved = await session.scalar(select(MonitorEventRecord))

    assert saved is not None
    assert saved.trace_id == "trace-1"
    assert saved.component == "model_gateway"
    assert saved.timeout is True
    assert saved.fallback is True
    assert saved.metadata_json == {"sensitivity": "internal"}

