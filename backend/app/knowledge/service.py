import hashlib
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.knowledge.chunking import chunk_pages
from app.knowledge.models import (
    Document,
    KnowledgeBase,
)
from app.knowledge.parsers import parse_document
from app.knowledge.vector_store import QdrantVectorStore
from app.shared.config import Settings


class DuplicateDocumentError(ValueError):
    pass


class InvalidUploadError(ValueError):
    pass


async def save_and_index_document(
    session: AsyncSession,
    vector_store: QdrantVectorStore,
    settings: Settings,
    knowledge_base_id: int,
    upload: UploadFile,
) -> Document:
    knowledge_base = await session.scalar(
        select(KnowledgeBase)
        .where(KnowledgeBase.id == knowledge_base_id)
        .options(selectinload(KnowledgeBase.permissions))
    )
    if knowledge_base is None:
        raise LookupError("knowledge base not found")

    filename = upload.filename or "unnamed"
    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt", ".md"}:
        raise InvalidUploadError("only pdf, docx, txt and md are supported")

    content = await upload.read()
    if not content:
        raise InvalidUploadError("empty file")
    if len(content) > settings.maximum_upload_bytes:
        raise InvalidUploadError("file is too large")

    sha256 = hashlib.sha256(content).hexdigest()
    duplicate = await session.scalar(
        select(Document).where(
            Document.knowledge_base_id == knowledge_base_id,
            Document.sha256 == sha256,
        )
    )
    if duplicate is not None:
        raise DuplicateDocumentError("same file already exists")

    settings.upload_directory.mkdir(
        parents=True,
        exist_ok=True,
    )
    stored_name = f"{sha256}{suffix}"
    storage_path = settings.upload_directory / stored_name
    storage_path.write_bytes(content)

    document = Document(
        knowledge_base_id=knowledge_base_id,
        filename=filename,
        storage_path=str(storage_path),
        sha256=sha256,
        status="PROCESSING",
        sensitivity=knowledge_base.sensitivity,
    )
    session.add(document)
    await session.flush()

    try:
        pages = parse_document(storage_path)
        if not pages:
            raise InvalidUploadError("no text could be extracted")

        roles = {
            permission.subject_value
            for permission in knowledge_base.permissions
            if permission.subject_type == "ROLE"
        }
        departments = {
            permission.subject_value
            for permission in knowledge_base.permissions
            if permission.subject_type == "DEPARTMENT"
        }
        chunks = chunk_pages(
            pages=pages,
            document_id=document.id,
            knowledge_base_id=knowledge_base_id,
            filename=filename,
            roles=roles,
            departments=departments,
            sensitivity=document.sensitivity,
        )
        await vector_store.upsert(chunks)
        document.status = "READY"
        await session.commit()
        await session.refresh(document)
        return document
    except Exception as exc:
        document.status = "FAILED"
        document.error_message = str(exc)[:1000]
        await session.commit()
        raise
