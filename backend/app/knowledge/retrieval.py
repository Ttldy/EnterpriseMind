from typing import Protocol

from app.knowledge.access import AccessContext
from app.knowledge.schemas import Citation
from app.knowledge.vector_store import VectorHit


class SearchableVectorStore(Protocol):
    async def search(
        self,
        query: str,
        access: AccessContext,
        limit: int = 5,
    ) -> list[VectorHit]: ...


class RetrievalService:
    def __init__(
        self,
        store: SearchableVectorStore,
        minimum_score: float,
    ) -> None:
        self._store = store
        self._minimum_score = minimum_score

    async def search(
        self,
        query: str,
        access: AccessContext,
        limit: int = 5,
    ) -> list[Citation]:
        hits = await self._store.search(
            query,
            access,
            limit,
        )
        return [
            Citation(
                document_id=hit.document_id,
                filename=hit.filename,
                page=hit.page,
                text=hit.text,
                score=hit.score,
                sensitivity=hit.sensitivity,
            )
            for hit in hits
            if hit.score >= self._minimum_score
        ]
