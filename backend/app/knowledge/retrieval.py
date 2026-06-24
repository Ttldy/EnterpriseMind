from dataclasses import dataclass
from typing import Protocol

from app.knowledge.access import AccessContext
from app.knowledge.evidence_gate import (
    EvidenceDecision,
    EvidenceGate,
)
from app.knowledge.fusion import FusedHit, fuse_hits
from app.knowledge.query_normalizer import RuleQueryNormalizer
from app.knowledge.query_rewriter import NoopQueryRewriter
from app.knowledge.reranker import ScoreReranker
from app.knowledge.schemas import Citation
from app.knowledge.vector_store import VectorHit


class SearchableVectorStore(Protocol):
    async def search(
        self,
        query: str,
        access: AccessContext,
        limit: int = 5,
    ) -> list[VectorHit]: ...


class QueryNormalizer(Protocol):
    def normalize(
        self,
        query: str,
    ) -> list[str]: ...


class QueryRewriter(Protocol):
    async def rewrite(
        self,
        query: str,
    ) -> list[str]: ...


class Reranker(Protocol):
    async def rerank(
        self,
        query: str,
        candidates: list[FusedHit],
    ) -> list[FusedHit]: ...


@dataclass(frozen=True)
class EnhancedRetrievalResult:
    queries: tuple[str, ...]
    candidates: tuple[FusedHit, ...]
    decision: EvidenceDecision


class RetrievalService:
    def __init__(
        self,
        store: SearchableVectorStore,
        minimum_score: float,
        normalizer: QueryNormalizer | None = None,
        rewriter: QueryRewriter | None = None,
        reranker: Reranker | None = None,
        gate: EvidenceGate | None = None,
    ) -> None:
        self._store = store
        self._minimum_score = minimum_score
        self._normalizer = normalizer or RuleQueryNormalizer()
        self._rewriter = rewriter or NoopQueryRewriter()
        self._reranker = reranker or ScoreReranker()
        self._gate = gate or EvidenceGate(
            full_answer_score=minimum_score,
            partial_answer_score=minimum_score,
            minimum_hit_count=1,
        )

    async def search(
        self,
        query: str,
        access: AccessContext,
        limit: int = 5,
    ) -> list[Citation]:
        result = await self.retrieve(
            query=query,
            access=access,
            limit=limit,
        )
        return result.decision.citations

    async def retrieve(
        self,
        query: str,
        access: AccessContext,
        limit: int = 5,
    ) -> EnhancedRetrievalResult:
        queries = await self._build_queries(query)
        query_hits: list[tuple[str, list[VectorHit]]] = []

        for item in queries:
            hits = await self._store.search(
                item,
                access,
                limit,
            )
            query_hits.append((item, hits))

        fused = fuse_hits(
            query_hits,
            limit=limit,
        )
        reranked = await self._reranker.rerank(
            query,
            fused,
        )
        decision = self._gate.evaluate(
            query,
            reranked,
        )
        return EnhancedRetrievalResult(
            queries=tuple(queries),
            candidates=tuple(reranked),
            decision=decision,
        )

    async def _build_queries(
        self,
        query: str,
    ) -> list[str]:
        normalized = self._normalizer.normalize(query)
        rewritten = await self._rewriter.rewrite(query)
        return _dedupe([query, *normalized, *rewritten])


def _dedupe(
    values: list[str],
) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = value.strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result
