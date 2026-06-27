from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import Role, User
from app.conversations.models import CitationRecord, Conversation, Message
from app.knowledge.models import Document, KnowledgeBase
from app.shared.database import get_session
from app.traces.api import router


def make_user(role: str) -> User:
    user = User(
        id=999,
        username=f"{role}01",
        password_hash="unused",
        department_id=1,
    )
    user.roles = [Role(name=role)]
    return user


def make_app(session_factory, user: User) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    async def override_user() -> User:
        return user

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_user
    return app


async def seed_trace(session_factory) -> str:
    trace_id = "trace-abc-123"
    async with session_factory() as session:
        user = await session.scalar(select(User).where(User.username == "it01"))
        assert user is not None
        knowledge_base = KnowledgeBase(name="Trace KB", domain="it")
        session.add(knowledge_base)
        await session.flush()
        document = Document(
            knowledge_base_id=knowledge_base.id,
            filename="vpn.md",
            storage_path="uploads/vpn.md",
            sha256="e" * 64,
            status="READY",
            sensitivity="internal",
        )
        conversation = Conversation(user_id=user.id, title="VPN")
        session.add_all([document, conversation])
        await session.flush()
        question = Message(
            conversation_id=conversation.id,
            role="user",
            content="VPN 无法连接怎么办？",
            trace_id=trace_id,
        )
        answer = Message(
            conversation_id=conversation.id,
            role="assistant",
            content="请先检查网络，再重新连接 VPN。",
            agent="it",
            model="qwen2.5:3b",
            trace_id=trace_id,
        )
        session.add_all([question, answer])
        await session.flush()
        session.add(
            CitationRecord(
                message_id=answer.id,
                document_id=document.id,
                filename=document.filename,
                page=1,
                text="VPN 故障排查",
                score=0.88,
            )
        )
        await session.commit()
    return trace_id


@pytest.mark.asyncio
async def test_admin_lists_and_reads_trace(seeded_session) -> None:
    trace_id = await seed_trace(seeded_session)
    app = make_app(seeded_session, make_user("admin"))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        list_response = await client.get(
            "/api/v1/admin/traces", params={"trace_id": trace_id}
        )
        detail_response = await client.get(
            f"/api/v1/admin/traces/{trace_id}"
        )

    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] == 1
    assert body["items"][0]["username"] == "it01"
    assert body["items"][0]["question"] == "VPN 无法连接怎么办？"
    assert body["items"][0]["citation_count"] == 1

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["user_message"] == "VPN 无法连接怎么办？"
    assert detail["assistant_message"] == "请先检查网络，再重新连接 VPN。"
    assert detail["citations"][0]["filename"] == "vpn.md"


@pytest.mark.asyncio
async def test_employee_cannot_read_global_traces(session_factory) -> None:
    app = make_app(session_factory, make_user("employee"))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        list_response = await client.get("/api/v1/admin/traces")
        detail_response = await client.get("/api/v1/admin/traces/trace-other")

    assert list_response.status_code == 403
    assert detail_response.status_code == 403


@pytest.mark.asyncio
async def test_missing_trace_returns_404(session_factory) -> None:
    app = make_app(session_factory, make_user("admin"))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/admin/traces/missing")

    assert response.status_code == 404
