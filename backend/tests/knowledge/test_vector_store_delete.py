from unittest.mock import AsyncMock

import pytest
from qdrant_client import models

from app.knowledge.vector_store import QdrantVectorStore


class StubEmbedding:
    dimensions = 3

    async def embed(self, text: str) -> list[float]:
        return [0.0, 0.0, 0.0]


@pytest.mark.asyncio
async def test_delete_documents_uses_document_id_filter() -> None:
    client = AsyncMock()
    store = QdrantVectorStore(
        client=client,
        collection_name="knowledge",
        embedding=StubEmbedding(),
    )

    await store.delete_documents([7, 3, 7])

    client.delete.assert_awaited_once()
    kwargs = client.delete.await_args.kwargs
    selector = kwargs["points_selector"]
    assert isinstance(selector, models.FilterSelector)
    condition = selector.filter.must[0]
    assert isinstance(condition, models.FieldCondition)
    assert condition.key == "document_id"
    assert isinstance(condition.match, models.MatchAny)
    assert condition.match.any == [3, 7]


@pytest.mark.asyncio
async def test_delete_documents_does_nothing_for_empty_list() -> None:
    client = AsyncMock()
    store = QdrantVectorStore(
        client=client,
        collection_name="knowledge",
        embedding=StubEmbedding(),
    )

    await store.delete_documents([])

    client.delete.assert_not_awaited()

