from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.auth.models import User
from app.monitoring.query_service import MonitoringQueryService
from app.monitoring.schemas import (
    ComponentHealthResponse,
    MonitoringEventResponse,
    MonitoringOverview,
)
from app.shared.config import Settings, get_settings
from app.shared.database import get_session

router = APIRouter(
    prefix="/admin/monitoring",
    tags=["admin-monitoring"],
)


def _service(
    session: AsyncSession, settings: Settings
) -> MonitoringQueryService:
    return MonitoringQueryService(
        session,
        latency_warning_ms=settings.monitor_latency_warning_ms,
    )


@router.get("/overview", response_model=MonitoringOverview)
async def overview(
    window_minutes: int | None = Query(default=None, ge=1, le=1440),
    _: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> MonitoringOverview:
    return await _service(session, settings).overview(
        window_minutes or settings.monitor_window_minutes
    )


@router.get("/components", response_model=ComponentHealthResponse)
async def components(
    window_minutes: int | None = Query(default=None, ge=1, le=1440),
    _: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ComponentHealthResponse:
    return await _service(session, settings).components(
        window_minutes or settings.monitor_window_minutes
    )


@router.get("/events", response_model=MonitoringEventResponse)
async def events(
    window_minutes: int | None = Query(default=None, ge=1, le=1440),
    component: str | None = None,
    success: bool | None = None,
    error_code: str | None = None,
    trace_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> MonitoringEventResponse:
    return await _service(session, settings).events(
        window_minutes=(
            window_minutes or settings.monitor_window_minutes
        ),
        component=component,
        success=success,
        error_code=error_code,
        trace_id=trace_id,
        limit=limit,
        offset=offset,
    )
