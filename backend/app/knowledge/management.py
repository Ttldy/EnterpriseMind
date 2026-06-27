from pathlib import Path
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.knowledge.models import Document, KnowledgeBase


class KnowledgeBaseNotFoundError(LookupError):
    pass


class KnowledgeBaseNameConflictError(ValueError):
    pass


class UnsafeDocumentPathError(ValueError):
    pass


class DocumentVectorStore(Protocol):
    async def delete_documents(self, document_ids: list[int]) -> None: ...


class KnowledgeBaseManagementService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        vector_store: DocumentVectorStore,
        upload_directory: Path,
    ) -> None:
        self._session = session
        self._vector_store = vector_store
        self._upload_directory = upload_directory

    async def rename(
        self,
        knowledge_base_id: int,
        name: str,
    ) -> KnowledgeBase:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("知识库名称不能为空")

        knowledge_base = await self._session.get(
            KnowledgeBase,
            knowledge_base_id,
        )
        if knowledge_base is None:
            raise KnowledgeBaseNotFoundError("知识库不存在")

        duplicate_id = await self._session.scalar(
            select(KnowledgeBase.id).where(
                KnowledgeBase.name == normalized_name,
                KnowledgeBase.id != knowledge_base_id,
            )
        )
        if duplicate_id is not None:
            raise KnowledgeBaseNameConflictError("知识库名称已存在")

        knowledge_base.name = normalized_name
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise KnowledgeBaseNameConflictError("知识库名称已存在") from exc
        await self._session.refresh(knowledge_base)
        return knowledge_base

    async def delete(self, knowledge_base_id: int) -> None:
        knowledge_base = await self._session.scalar(
            select(KnowledgeBase)
            .where(KnowledgeBase.id == knowledge_base_id)
            .options(
                selectinload(KnowledgeBase.documents),
                selectinload(KnowledgeBase.permissions),
            )
            .with_for_update()
        )
        if knowledge_base is None:
            raise KnowledgeBaseNotFoundError("知识库不存在")

        document_ids = [item.id for item in knowledge_base.documents]
        paths = [self._safe_document_path(item) for item in knowledge_base.documents]

        await self._vector_store.delete_documents(document_ids)
        await self._session.delete(knowledge_base)
        await self._session.commit()

        for path in paths:
            try:
                path.unlink()
            except FileNotFoundError:
                continue

    def _safe_document_path(self, document: Document) -> Path:
        root = self._upload_directory.resolve()
        path = Path(document.storage_path).resolve()
        if not path.is_relative_to(root):
            raise UnsafeDocumentPathError(
                f"文档路径不在上传目录内: {document.id}"
            )
        return path

