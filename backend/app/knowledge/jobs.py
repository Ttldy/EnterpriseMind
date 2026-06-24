import asyncio
from pathlib import Path

from qdrant_client import AsyncQdrantClient
from rq import get_current_job
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.knowledge.chunking import chunk_pages
from app.knowledge.embedding import (
    OllamaEmbeddingProvider,
)
from app.knowledge.models import (
    Document,
    KnowledgeBase,
)
from app.knowledge.parsers import parse_document
from app.knowledge.vector_store import (
    QdrantVectorStore,
)
from app.shared.config import get_settings
from app.shared.database import SessionFactory


def clean_error(exc: Exception) -> str:
    text = f"{type(exc).__name__}: {exc}"
    return text.replace(
        get_settings().database_url,
        "[DATABASE_URL]",
    )[:1000]


async def process_document(
    document_id: int,
) -> None:
    settings = get_settings()
    client = AsyncQdrantClient(
        url=settings.qdrant_url
    )
    store = QdrantVectorStore(
        client=client,
        collection_name=(
            settings.qdrant_collection
        ),
        embedding=OllamaEmbeddingProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_embedding_model,
            dimensions=settings.embedding_dimensions,
            timeout_seconds=(
                settings.ollama_embedding_timeout_seconds
            ),
        ),
    )
    job = get_current_job()

    try:
        async with SessionFactory() as session:
            document = await session.scalar(
                select(Document)
                .where(Document.id == document_id)
                .options(
                    selectinload(
                        Document.knowledge_base
                    ).selectinload(
                        KnowledgeBase.permissions
                    )
                )
            )
            if document is None:
                raise LookupError(
                    "document not found"
                )

            document.attempts += 1
            document.status = "PROCESSING"
            document.error_message = None
            if job is not None:
                job.meta["attempts"] = (
                    document.attempts
                )
                job.save_meta()  # type: ignore[no-untyped-call]
            await session.commit()

            path = Path(document.storage_path)
            pages = parse_document(path)
            if not pages:
                raise ValueError(
                    "no text could be extracted"
                )

            permissions = (
                document.knowledge_base.permissions
            )
            roles = {
                item.subject_value
                for item in permissions
                if item.subject_type == "ROLE"
            }
            departments = {
                item.subject_value
                for item in permissions
                if item.subject_type == "DEPARTMENT"
            }
            chunks = chunk_pages(
                pages=pages,
                document_id=document.id,
                knowledge_base_id=(
                    document.knowledge_base_id
                ),
                filename=document.filename,
                roles=roles,
                departments=departments,
                sensitivity=document.sensitivity,
            )

            await store.delete_document(document.id)
            await store.upsert(chunks)
            document.status = "READY"
            await session.commit()
    except Exception as exc:
        async with SessionFactory() as session:
            document = await session.get(
                Document,
                document_id,
            )
            if document is not None:
                document.status = "FAILED"
                document.error_message = clean_error(
                    exc
                )
                await session.commit()
        raise
    finally:
        await client.close()


def process_document_job(
    document_id: int,
) -> None:
    asyncio.run(process_document(document_id))
