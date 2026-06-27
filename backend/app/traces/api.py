from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.auth.models import User
from app.shared.database import get_session
from app.traces.schemas import TraceDetail, TraceListResponse
from app.traces.service import TraceNotFoundError, TraceService

router = APIRouter(
    prefix="/admin/traces",
    tags=["admin-traces"],
)


@router.get("", response_model=TraceListResponse)
async def list_traces(
    trace_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> TraceListResponse:
    return await TraceService(session).list(
        trace_id=trace_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{trace_id}", response_model=TraceDetail)
async def get_trace(
    trace_id: str,
    _: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> TraceDetail:
    try:
        return await TraceService(session).get(trace_id)
    except TraceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

