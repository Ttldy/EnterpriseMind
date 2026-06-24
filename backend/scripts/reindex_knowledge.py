import asyncio
from pathlib import Path

from qdrant_client import AsyncQdrantClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.knowledge.chunking import chunk_pages
from app.knowledge.embedding import OllamaEmbeddingProvider
from app.knowledge.models import (
    Document,
    KnowledgeBase,
)
from app.knowledge.parsers import parse_document
from app.knowledge.vector_store import QdrantVectorStore
from app.shared.config import get_settings
from app.shared.database import SessionFactory


async def main() -> None:
    settings = get_settings()
    client = AsyncQdrantClient(
        url=settings.qdrant_url
    )
    store = QdrantVectorStore(
        client=client,
        collection_name=settings.qdrant_collection,
        embedding=OllamaEmbeddingProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_embedding_model,
            dimensions=settings.embedding_dimensions,
            timeout_seconds=(
                settings.ollama_embedding_timeout_seconds
            ),
        ),
    )

    indexed = 0
    skipped = 0
    try:
        await store.ensure_collection()
        async with SessionFactory() as session:
            documents = list(
                (
                    await session.scalars(
                        select(Document)
                        .where(Document.status == "READY")
                        .options(
                            selectinload(
                                Document.knowledge_base
                            ).selectinload(
                                KnowledgeBase.permissions
                            )
                        )
                    )
                ).all()
            )

            for document in documents:
                path = Path(document.storage_path)
                if not path.exists():
                    skipped += 1
                    print(
                        f"skip missing file: document_id={document.id} path={path}"
                    )
                    continue

                pages = parse_document(path)
                if not pages:
                    skipped += 1
                    print(
                        f"skip empty document: document_id={document.id}"
                    )
                    continue

                permissions = document.knowledge_base.permissions
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
                indexed += 1
                print(
                    f"indexed document_id={document.id} chunks={len(chunks)}"
                )
    finally:
        await client.close()

    print(
        f"reindex finished: indexed={indexed}, skipped={skipped}, "
        f"collection={settings.qdrant_collection}"
    )


if __name__ == "__main__":
    asyncio.run(main())
