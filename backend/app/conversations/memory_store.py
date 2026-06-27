from uuid import NAMESPACE_URL, uuid5

from qdrant_client import AsyncQdrantClient, models

from app.conversations.memory_schemas import (
    MemoryRecord,
    MemorySearchHit,
)
from app.knowledge.embedding import EmbeddingProvider


class QdrantLongTermMemoryStore:
    def __init__(
        self,
        client: AsyncQdrantClient,
        collection_name: str,
        embedding: EmbeddingProvider,
    ) -> None:
        self._client = client
        self._collection_name = collection_name
        self._embedding = embedding

    async def ensure_collection(self) -> None:
        exists = await self._client.collection_exists(
            self._collection_name
        )
        if exists:
            return

        await self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=models.VectorParams(
                size=self._embedding.dimensions,
                distance=models.Distance.COSINE,
            ),
        )

    async def upsert(
        self,
        record: MemoryRecord,
    ) -> None:
        vector = await self._embedding.embed(record.text)
        payload = {
            "user_id": record.user_id,
            "department": record.department,
            "roles": list(record.roles),
            "conversation_id": record.conversation_id,
            "message_ids": list(record.message_ids),
            "memory_type": record.memory_type,
            "sensitivity": record.sensitivity,
            "created_at": record.created_at.isoformat(),
            "text": record.text,
            "share_scope": record.share_scope,
        }
        point_id = str(
            uuid5(
                NAMESPACE_URL,
                (
                    f"memory:{record.user_id}:"
                    f"{record.conversation_id}:"
                    f"{','.join(str(item) for item in record.message_ids)}:"
                    f"{record.memory_type}:{record.text}"
                ),
            )
        )
        await self._client.upsert(
            collection_name=self._collection_name,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            ],
            wait=True,
        )

    async def search_private(
        self,
        query: str,
        user_id: int,
        limit: int,
        minimum_score: float,
    ) -> list[MemorySearchHit]:
        vector = await self._embedding.embed(query)
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=user_id),
                ),
                models.FieldCondition(
                    key="share_scope",
                    match=models.MatchValue(value="private"),
                ),
            ]
        )
        response = await self._client.query_points(
            collection_name=self._collection_name,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )

        hits: list[MemorySearchHit] = []
        for point in response.points:
            if float(point.score) < minimum_score:
                continue
            payload = point.payload or {}
            hits.append(
                MemorySearchHit(
                    text=str(payload.get("text", "")),
                    score=float(point.score),
                    memory_type=str(
                        payload.get(
                            "memory_type",
                            "conversation_summary",
                        )
                    ),
                    sensitivity=str(
                        payload.get("sensitivity", "internal")
                    ),
                )
            )
        return [hit for hit in hits if hit.text]
