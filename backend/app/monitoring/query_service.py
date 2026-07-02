from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.monitoring.contracts import MonitorEvent, sanitize_metadata
from app.monitoring.models import MonitorEventRecord
from app.monitoring.schemas import (
    ComponentHealth,
    ComponentHealthResponse,
    MonitoringEventItem,
    MonitoringEventResponse,
    MonitoringOverview,
)
from app.monitoring.scoring import HealthMetrics, HealthScorer


class MonitoringQueryService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        latency_warning_ms: int,
    ) -> None:
        self._session = session
        self._scorer = HealthScorer(latency_warning_ms)

    async def overview(self, window_minutes: int) -> MonitoringOverview:
        now = datetime.now(UTC)
        events = await self._window_events(window_minutes, now)
        result = self._scorer.score(
            events,
            component="overall",
            window_minutes=window_minutes,
            now=now,
        )
        return MonitoringOverview(
            window_minutes=window_minutes,
            overall_health_score=result.health_score,
            overall_status=result.status.value,
            total_events=result.event_count,
            success_rate=result.success_rate,
            average_latency_ms=result.average_latency_ms,
            p95_latency_ms=result.p95_latency_ms,
            timeout_rate=result.timeout_rate,
            fallback_rate=result.fallback_rate,
            circuit_open_rate=result.circuit_open_rate,
            reasons=list(result.reasons),
            penalties=result.penalties,
            generated_at=now,
        )

    async def components(
        self, window_minutes: int
    ) -> ComponentHealthResponse:
        now = datetime.now(UTC)
        events = await self._window_events(window_minutes, now)
        names = sorted({event.component for event in events})
        items = [
            self._component_schema(
                self._scorer.score(
                    events,
                    component=name,
                    window_minutes=window_minutes,
                    now=now,
                )
            )
            for name in names
        ]
        return ComponentHealthResponse(
            window_minutes=window_minutes,
            items=items,
            generated_at=now,
        )

    async def events(
        self,
        *,
        window_minutes: int,
        component: str | None,
        success: bool | None,
        error_code: str | None,
        trace_id: str | None,
        limit: int,
        offset: int,
    ) -> MonitoringEventResponse:
        cutoff = datetime.now(UTC) - timedelta(minutes=window_minutes)
        conditions = [MonitorEventRecord.created_at >= cutoff]
        if component:
            conditions.append(MonitorEventRecord.component == component.strip())
        if success is not None:
            conditions.append(MonitorEventRecord.success.is_(success))
        if error_code:
            conditions.append(MonitorEventRecord.error_code == error_code.strip())
        if trace_id:
            conditions.append(MonitorEventRecord.trace_id == trace_id.strip())
        total = int(
            await self._session.scalar(
                select(func.count(MonitorEventRecord.id)).where(*conditions)
            )
            or 0
        )
        rows = (
            await self._session.scalars(
                select(MonitorEventRecord)
                .where(*conditions)
                .order_by(
                    MonitorEventRecord.created_at.desc(),
                    MonitorEventRecord.id.desc(),
                )
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return MonitoringEventResponse(
            items=[self._event_schema(row) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def _window_events(
        self, window_minutes: int, now: datetime
    ) -> list[MonitorEvent]:
        cutoff = now - timedelta(minutes=window_minutes)
        rows = (
            await self._session.scalars(
                select(MonitorEventRecord).where(
                    MonitorEventRecord.created_at >= cutoff
                )
            )
        ).all()
        return [self._event(row) for row in rows]

    @staticmethod
    def _event(row: MonitorEventRecord) -> MonitorEvent:
        created_at = row.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        return MonitorEvent(
            trace_id=row.trace_id,
            component=row.component,
            operation=row.operation,
            success=row.success,
            latency_ms=row.latency_ms,
            error_code=row.error_code,
            agent=row.agent,
            provider=row.provider,
            model=row.model,
            timeout=row.timeout,
            cache_hit=row.cache_hit,
            fallback=row.fallback,
            circuit_open=row.circuit_open,
            created_at=created_at,
            metadata=row.metadata_json,
        )

    @staticmethod
    def _component_schema(result: HealthMetrics) -> ComponentHealth:
        return ComponentHealth(
            component=result.component,
            event_count=result.event_count,
            success_rate=result.success_rate,
            average_latency_ms=result.average_latency_ms,
            p95_latency_ms=result.p95_latency_ms,
            timeout_rate=result.timeout_rate,
            fallback_rate=result.fallback_rate,
            circuit_open_rate=result.circuit_open_rate,
            health_score=result.health_score,
            status=result.status.value,
            reasons=list(result.reasons),
            penalties=result.penalties,
        )

    @staticmethod
    def _event_schema(row: MonitorEventRecord) -> MonitoringEventItem:
        return MonitoringEventItem(
            id=row.id,
            trace_id=row.trace_id,
            component=row.component,
            operation=row.operation,
            success=row.success,
            latency_ms=row.latency_ms,
            error_code=row.error_code,
            agent=row.agent,
            provider=row.provider,
            model=row.model,
            timeout=row.timeout,
            cache_hit=row.cache_hit,
            fallback=row.fallback,
            circuit_open=row.circuit_open,
            metadata=sanitize_metadata(row.metadata_json),
            created_at=row.created_at,
        )
