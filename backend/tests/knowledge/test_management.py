from pathlib import Path

import pytest
from sqlalchemy import select

from app.knowledge.management import (
    KnowledgeBaseManagementService,
    KnowledgeBaseNameConflictError,
)
from app.knowledge.models import Document, KnowledgeBase, KnowledgePermission


class RecordingVectorStore:
    def __init__(self, *, fail: bool = False) -> None:
        self.deleted_document_ids: list[int] = []
        self.fail = fail

    async def delete_documents(self, document_ids: list[int]) -> None:
        if self.fail:
            raise RuntimeError("qdrant unavailable")
        self.deleted_document_ids.extend(document_ids)


def make_document(knowledge_base_id: int, path: Path, sha: str) -> Document:
    return Document(
        knowledge_base_id=knowledge_base_id,
        filename=path.name,
        storage_path=str(path),
        sha256=sha,
        status="READY",
        sensitivity="internal",
    )


@pytest.mark.asyncio
async def test_rename_trims_name_and_rejects_duplicate(
    session_factory,
    tmp_path,
) -> None:
    async with session_factory() as session:
        first = KnowledgeBase(name="IT", domain="it")
        second = KnowledgeBase(name="HR", domain="hr")
        session.add_all([first, second])
        await session.commit()

        service = KnowledgeBaseManagementService(
            session=session,
            vector_store=RecordingVectorStore(),
            upload_directory=tmp_path,
        )
        renamed = await service.rename(first.id, "  IT Support  ")
        assert renamed.name == "IT Support"

        with pytest.raises(KnowledgeBaseNameConflictError):
            await service.rename(first.id, " HR ")


@pytest.mark.asyncio
async def test_delete_removes_only_target_base_vectors_and_files(
    session_factory,
    tmp_path,
) -> None:
    target_path = tmp_path / "target.md"
    target_path.write_text("target", encoding="utf-8")
    other_path = tmp_path / "other.md"
    other_path.write_text("other", encoding="utf-8")

    async with session_factory() as session:
        target = KnowledgeBase(name="Target", domain="it")
        other = KnowledgeBase(name="Other", domain="hr")
        session.add_all([target, other])
        await session.flush()
        target_document = make_document(target.id, target_path, "a" * 64)
        other_document = make_document(other.id, other_path, "b" * 64)
        session.add_all(
            [
                target_document,
                other_document,
                KnowledgePermission(
                    knowledge_base_id=target.id,
                    subject_type="ROLE",
                    subject_value="it_staff",
                ),
            ]
        )
        await session.commit()
        target_id = target.id
        other_id = other.id
        target_document_id = target_document.id
        other_document_id = other_document.id

        store = RecordingVectorStore()
        service = KnowledgeBaseManagementService(
            session=session,
            vector_store=store,
            upload_directory=tmp_path,
        )
        await service.delete(target_id)

        assert store.deleted_document_ids == [target_document_id]
        assert await session.get(KnowledgeBase, target_id) is None
        assert await session.get(Document, target_document_id) is None
        assert await session.get(KnowledgeBase, other_id) is not None
        assert await session.get(Document, other_document_id) is not None
        assert not target_path.exists()
        assert other_path.exists()
        permissions = (
            await session.scalars(
                select(KnowledgePermission).where(
                    KnowledgePermission.knowledge_base_id == target_id
                )
            )
        ).all()
        assert permissions == []


@pytest.mark.asyncio
async def test_qdrant_failure_keeps_database_and_file(
    session_factory,
    tmp_path,
) -> None:
    path = tmp_path / "keep.md"
    path.write_text("keep", encoding="utf-8")

    async with session_factory() as session:
        knowledge_base = KnowledgeBase(name="Keep", domain="it")
        session.add(knowledge_base)
        await session.flush()
        document = make_document(knowledge_base.id, path, "c" * 64)
        session.add(document)
        await session.commit()

        service = KnowledgeBaseManagementService(
            session=session,
            vector_store=RecordingVectorStore(fail=True),
            upload_directory=tmp_path,
        )
        with pytest.raises(RuntimeError, match="qdrant unavailable"):
            await service.delete(knowledge_base.id)

        assert await session.get(KnowledgeBase, knowledge_base.id) is not None
        assert await session.get(Document, document.id) is not None
        assert path.exists()

