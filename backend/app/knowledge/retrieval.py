import asyncio
from dataclasses import dataclass, field
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
from app.monitoring.contracts import MonitorRecorder
from app.monitoring.instrumentation import (
    OperationTimer,
    exception_error_code,
    is_timeout_error,
)


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
    diagnostics: dict[str, object] = field(
        default_factory=dict
    )


class RetrievalService:
    def __init__(
        self,
        store: SearchableVectorStore,
        minimum_score: float,
        normalizer: QueryNormalizer | None = None,
        rewriter: QueryRewriter | None = None,
        reranker: Reranker | None = None,
        gate: EvidenceGate | None = None,
        max_queries: int = 4,
        recall_per_query: int = 5,
        monitor: MonitorRecorder | None = None,
    ) -> None:
        self._store = store
        self._minimum_score = minimum_score
        self._normalizer = normalizer or RuleQueryNormalizer()
        self._rewriter = rewriter or NoopQueryRewriter()
        self._reranker = reranker or ScoreReranker()
        self._max_queries = max(1, max_queries)
        self._recall_per_query = max(
            1,
            recall_per_query,
        )
        self._monitor = monitor
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
        timer = OperationTimer(
            self._monitor,
            component="retrieval",
            operation="retrieve",
        )
        try:
            result = await self._retrieve(
                query,
                access,
                limit,
            )
        except Exception as exc:
            timer.finish(
                success=False,
                error_code=exception_error_code(exc),
                timeout=is_timeout_error(exc),
            )
            raise
        timer.finish(
            success=True,
            error_code=(
                "evidence_insufficient"
                if result.decision.level.value
                == "insufficient"
                else None
            ),
            metadata={
                **result.diagnostics,
                "citation_count": len(
                    result.decision.citations
                ),
                "evidence_level": (
                    result.decision.level.value
                ),
                **(
                    {
                        "business_outcome": (
                            "evidence_insufficient"
                        )
                    }
                    if result.decision.level.value
                    == "insufficient"
                    else {}
                ),
            },
        )
        return result

    async def _retrieve(
        self,
        query: str,
        access: AccessContext,
        limit: int = 5,
    ) -> EnhancedRetrievalResult:
        queries = await self._build_queries(query)
        query_hits: list[tuple[str, list[VectorHit]]] = []
        responses = await asyncio.gather(
            *(
                self._store.search(
                    item,
                    access,
                    self._recall_per_query,
                )
                for item in queries
            ),
            return_exceptions=True,
        )
        failed_query_count = 0
        for item, response in zip(
            queries,
            responses,
            strict=True,
        ):
            if isinstance(response, BaseException):
                failed_query_count += 1
                continue
            query_hits.append((item, response))

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
            diagnostics={
                "query_count": len(queries),
                "successful_query_count": len(query_hits),
                "failed_query_count": failed_query_count,
                "executed_queries": tuple(queries),
            },
        )

    async def _build_queries(
        self,
        query: str,
    ) -> list[str]:
        normalized = self._normalizer.normalize(query)
        try:
            rewritten = await self._rewriter.rewrite(query)
        except Exception:
            rewritten = []
        return _dedupe(
            [query, *normalized, *rewritten],
            limit=self._max_queries,
        )


def _dedupe(
    values: list[str],
    limit: int | None = None,
) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = " ".join(value.split()).strip()
        key = item.casefold()
        if item and key not in seen:
            seen.add(key)
            result.append(item)
            if limit is not None and len(result) >= limit:
                break
    return result
