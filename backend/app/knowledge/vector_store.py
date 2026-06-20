from dataclasses import dataclass
from typing import cast
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import AsyncQdrantClient, models

from app.knowledge.access import AccessContext
from app.knowledge.chunking import Chunk
from app.knowledge.embedding import EmbeddingProvider


@dataclass(frozen=True)
class VectorHit:
    document_id: int
    filename: str
    page: int
    text: str
    score: float
    sensitivity: str


class QdrantVectorStore:
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
        exists = await self._client.collection_exists(self._collection_name)
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
        chunks: list[Chunk],
    ) -> None:
        points: list[models.PointStruct] = []

        for chunk in chunks:
            vector = await self._embedding.embed(chunk.text)
            document_id = int(
                cast(
                    int | str,
                    chunk.payload["document_id"],
                )
            )
            point_id = str(
                uuid5(
                    NAMESPACE_URL,
                    f"{document_id}:{chunk.chunk_index}",
                )
            )
            payload = dict(chunk.payload)
            payload["text"] = chunk.text
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            )

        if points:
            await self._client.upsert(
                collection_name=self._collection_name,
                points=points,
                wait=True,
            )

    async def search(
        self,
        query: str,
        access: AccessContext,
        limit: int = 5,
    ) -> list[VectorHit]:
        if not access.knowledge_base_ids:
            return []

        vector = await self._embedding.embed(query)
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="knowledge_base_id",
                    match=models.MatchAny(any=sorted(access.knowledge_base_ids)),
                )
            ]
        )

        response = await self._client.query_points(
            collection_name=self._collection_name,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )

        hits: list[VectorHit] = []
        for point in response.points:
            payload = point.payload or {}
            hits.append(
                VectorHit(
                    document_id=int(payload["document_id"]),
                    filename=str(payload["filename"]),
                    page=int(payload["page"]),
                    text=str(payload["text"]),
                    score=float(point.score),
                    sensitivity=str(payload["sensitivity"]),
                )
            )
        return hits

    async def delete_document(
        self,
        document_id: int,
    ) -> None:
        await self._client.delete(
            collection_name=self._collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
            wait=True,
        )
