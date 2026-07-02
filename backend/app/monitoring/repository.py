from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.monitoring.contracts import MonitorEvent
from app.monitoring.models import MonitorEventRecord


class PostgresMonitorWriter:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def write(
        self,
        events: list[MonitorEvent],
    ) -> None:
        if not events:
            return
        async with self._session_factory() as session:
            session.add_all(
                [
                    MonitorEventRecord(
                        trace_id=event.trace_id,
                        component=event.component,
                        operation=event.operation,
                        success=event.success,
                        latency_ms=event.latency_ms,
                        error_code=event.error_code,
                        agent=event.agent,
                        provider=event.provider,
                        model=event.model,
                        timeout=event.timeout,
                        cache_hit=event.cache_hit,
                        fallback=event.fallback,
                        circuit_open=event.circuit_open,
                        metadata_json=event.metadata,
                        created_at=event.created_at,
                    )
                    for event in events
                ]
            )
            await session.commit()

