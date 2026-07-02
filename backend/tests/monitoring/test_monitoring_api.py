from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import Role, User
from app.monitoring.api import router
from app.monitoring.models import MonitorEventRecord
from app.shared.database import get_session


def _user(role: str) -> User:
    user = User(
        id=900,
        username=f"{role}01",
        password_hash="unused",
        department_id=1,
    )
    user.roles = [Role(name=role)]
    return user


def _app(session_factory, role: str) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    async def user_override() -> User:
        return _user(role)

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_current_user] = user_override
    return app


async def _seed(session_factory) -> None:
    now = datetime.now(UTC)
    async with session_factory() as session:
        session.add_all(
            [
                MonitorEventRecord(
                    trace_id="trace-monitor-1",
                    component="tool_manager",
                    operation="knowledge_search",
                    success=False,
                    latency_ms=2500,
                    error_code="tool_timeout",
                    timeout=True,
                    cache_hit=False,
                    fallback=True,
                    circuit_open=False,
                    metadata_json={"tool_name": "knowledge_search"},
                    created_at=now,
                ),
                MonitorEventRecord(
                    trace_id="trace-old",
                    component="retrieval",
                    operation="retrieve",
                    success=True,
                    latency_ms=20,
                    timeout=False,
                    cache_hit=False,
                    fallback=False,
                    circuit_open=False,
                    metadata_json={},
                    created_at=now - timedelta(minutes=30),
                ),
            ]
        )
        await session.commit()


@pytest.mark.asyncio
async def test_admin_reads_real_monitoring_views(session_factory) -> None:
    await _seed(session_factory)
    app = _app(session_factory, "admin")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        overview = await client.get(
            "/api/v1/admin/monitoring/overview",
            params={"window_minutes": 5},
        )
        components = await client.get(
            "/api/v1/admin/monitoring/components"
        )
        events = await client.get(
            "/api/v1/admin/monitoring/events",
            params={
                "trace_id": "trace-monitor-1",
                "component": "tool_manager",
            },
        )

    assert overview.status_code == 200
    assert overview.json()["total_events"] == 1
    assert overview.json()["overall_status"] == "DEGRADED"
    assert components.status_code == 200
    assert components.json()["items"][0]["component"] == "tool_manager"
    assert events.status_code == 200
    body = events.json()
    assert body["total"] == 1
    assert body["items"][0]["trace_id"] == "trace-monitor-1"
    serialized = str(body).casefold()
    assert "question" not in serialized
    assert "answer" not in serialized
    assert "prompt" not in serialized
    assert "sql_result" not in serialized


@pytest.mark.asyncio
async def test_employee_cannot_read_monitoring(session_factory) -> None:
    app = _app(session_factory, "employee")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        responses = [
            await client.get("/api/v1/admin/monitoring/overview"),
            await client.get("/api/v1/admin/monitoring/components"),
            await client.get("/api/v1/admin/monitoring/events"),
        ]
    assert [item.status_code for item in responses] == [403, 403, 403]


@pytest.mark.asyncio
async def test_empty_window_returns_no_data(session_factory) -> None:
    app = _app(session_factory, "admin")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/admin/monitoring/overview"
        )
    assert response.status_code == 200
    assert response.json()["overall_status"] == "NO_DATA"
    assert response.json()["overall_health_score"] is None


@pytest.mark.asyncio
async def test_events_support_pagination_and_success_filter(
    session_factory,
) -> None:
    await _seed(session_factory)
    app = _app(session_factory, "admin")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/admin/monitoring/events",
            params={"success": False, "limit": 1, "offset": 0},
        )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["items"]) == 1
