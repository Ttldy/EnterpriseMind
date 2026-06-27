from types import SimpleNamespace

import pytest
from qdrant_client import models

from app.conversations.memory_schemas import MemoryRecord
from app.conversations.memory_store import QdrantLongTermMemoryStore


class FakeEmbedding:
    dimensions = 3

    async def embed(
        self,
        text: str,
    ) -> list[float]:
        del text
        return [0.1, 0.2, 0.3]


class FakeQdrantClient:
    def __init__(self) -> None:
        self.created_collection: str | None = None
        self.upserted_points: list[models.PointStruct] = []
        self.last_query_filter: models.Filter | None = None

    async def collection_exists(
        self,
        collection_name: str,
    ) -> bool:
        del collection_name
        return False

    async def create_collection(
        self,
        collection_name: str,
        vectors_config: models.VectorParams,
    ) -> None:
        del vectors_config
        self.created_collection = collection_name

    async def upsert(
        self,
        collection_name: str,
        points: list[models.PointStruct],
        wait: bool,
    ) -> None:
        del collection_name, wait
        self.upserted_points.extend(points)

    async def query_points(
        self,
        collection_name: str,
        query: list[float],
        query_filter: models.Filter,
        limit: int,
        with_payload: bool,
    ):
        del collection_name, query, limit, with_payload
        self.last_query_filter = query_filter
        return SimpleNamespace(points=[])


@pytest.mark.asyncio
async def test_memory_store_writes_user_id_payload() -> None:
    client = FakeQdrantClient()
    store = QdrantLongTermMemoryStore(
        client=client,
        collection_name="enterprise_conversation_memory_v1",
        embedding=FakeEmbedding(),
    )

    await store.upsert(
        MemoryRecord(
            user_id=7,
            department="IT",
            roles=("employee", "it_staff"),
            conversation_id=11,
            message_ids=(101, 102),
            memory_type="conversation_summary",
            sensitivity="internal",
            text="用户偏好直接给 VPN 排查步骤。",
        )
    )

    payload = client.upserted_points[0].payload
    assert payload["user_id"] == 7
    assert payload["department"] == "IT"
    assert payload["roles"] == ["employee", "it_staff"]
    assert payload["conversation_id"] == 11
    assert payload["message_ids"] == [101, 102]
    assert payload["memory_type"] == "conversation_summary"
    assert payload["sensitivity"] == "internal"
    assert payload["share_scope"] == "private"
    assert payload["text"] == "用户偏好直接给 VPN 排查步骤。"


@pytest.mark.asyncio
async def test_memory_store_search_filters_by_user_id() -> None:
    client = FakeQdrantClient()
    store = QdrantLongTermMemoryStore(
        client=client,
        collection_name="enterprise_conversation_memory_v1",
        embedding=FakeEmbedding(),
    )

    await store.search_private(
        query="VPN 没有连接",
        user_id=7,
        limit=3,
        minimum_score=0.25,
    )

    assert client.last_query_filter is not None
    conditions = client.last_query_filter.must
    assert conditions is not None
    assert any(
        condition.key == "user_id"
        and isinstance(condition.match, models.MatchValue)
        and condition.match.value == 7
        for condition in conditions
    )
