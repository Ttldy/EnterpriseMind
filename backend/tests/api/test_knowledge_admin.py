from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import Role, User
from app.knowledge.api import router
from app.knowledge.models import Document, KnowledgeBase
from app.shared.database import get_session


class RecordingVectorStore:
    def __init__(self) -> None:
        self.deleted_document_ids: list[int] = []

    async def delete_documents(self, document_ids: list[int]) -> None:
        self.deleted_document_ids.extend(document_ids)


def make_user(role: str) -> User:
    user = User(
        id=1,
        username=f"{role}01",
        password_hash="unused",
        department_id=1,
    )
    user.roles = [Role(name=role)]
    return user


def make_app(session_factory, user: User, store: RecordingVectorStore) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.state.vector_store = store

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    async def override_user() -> User:
        return user

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_user
    return app


@pytest.mark.asyncio
async def test_admin_can_rename_knowledge_base(session_factory) -> None:
    async with session_factory() as session:
        knowledge_base = KnowledgeBase(name="Old", domain="it")
        session.add(knowledge_base)
        await session.commit()
        knowledge_base_id = knowledge_base.id

    app = make_app(session_factory, make_user("admin"), RecordingVectorStore())
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.patch(
            f"/api/v1/knowledge/bases/{knowledge_base_id}",
            json={"name": "  New Name  "},
        )

    assert response.status_code == 200
    assert response.json() == {"id": knowledge_base_id, "name": "New Name"}
    async with session_factory() as session:
        assert (await session.get(KnowledgeBase, knowledge_base_id)).name == "New Name"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [({"name": "   "}, 422), ({"name": "Taken"}, 409)],
)
async def test_rename_validates_name(
    session_factory,
    payload: dict[str, str],
    expected_status: int,
) -> None:
    async with session_factory() as session:
        target = KnowledgeBase(name="Target", domain="it")
        taken = KnowledgeBase(name="Taken", domain="hr")
        session.add_all([target, taken])
        await session.commit()
        target_id = target.id

    app = make_app(session_factory, make_user("admin"), RecordingVectorStore())
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.patch(
            f"/api/v1/knowledge/bases/{target_id}", json=payload
        )

    assert response.status_code == expected_status


@pytest.mark.asyncio
async def test_non_admin_cannot_rename_or_delete(session_factory) -> None:
    app = make_app(session_factory, make_user("employee"), RecordingVectorStore())
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        rename_response = await client.patch(
            "/api/v1/knowledge/bases/1", json={"name": "No"}
        )
        delete_response = await client.delete("/api/v1/knowledge/bases/1")

    assert rename_response.status_code == 403
    assert delete_response.status_code == 403


@pytest.mark.asyncio
async def test_admin_delete_returns_204_and_removes_target(session_factory, tmp_path) -> None:
    path = Path(tmp_path) / "delete.md"
    path.write_text("delete", encoding="utf-8")
    async with session_factory() as session:
        knowledge_base = KnowledgeBase(name="Delete", domain="it")
        session.add(knowledge_base)
        await session.flush()
        document = Document(
            knowledge_base_id=knowledge_base.id,
            filename=path.name,
            storage_path=str(path),
            sha256="d" * 64,
            status="READY",
            sensitivity="internal",
        )
        session.add(document)
        await session.commit()
        knowledge_base_id = knowledge_base.id
        document_id = document.id

    store = RecordingVectorStore()
    app = make_app(session_factory, make_user("admin"), store)
    app.state.upload_directory = tmp_path
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.delete(
            f"/api/v1/knowledge/bases/{knowledge_base_id}"
        )

    assert response.status_code == 204
    assert store.deleted_document_ids == [document_id]
    async with session_factory() as session:
        assert await session.get(KnowledgeBase, knowledge_base_id) is None


@pytest.mark.asyncio
async def test_delete_missing_knowledge_base_returns_404(session_factory) -> None:
    app = make_app(session_factory, make_user("admin"), RecordingVectorStore())
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.delete("/api/v1/knowledge/bases/999")

    assert response.status_code == 404

