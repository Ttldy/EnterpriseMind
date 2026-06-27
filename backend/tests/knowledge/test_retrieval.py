import asyncio

import pytest

from app.knowledge.access import AccessContext
from app.knowledge.evidence_gate import EvidenceLevel
from app.knowledge.retrieval import RetrievalService
from app.knowledge.vector_store import VectorHit


class FakeStore:
    def __init__(
        self,
        hits: list[VectorHit],
    ) -> None:
        self.hits = hits
        self.calls: list[tuple[str, AccessContext]] = []

    async def search(
        self,
        query: str,
        access: AccessContext,
        limit: int = 5,
    ) -> list[VectorHit]:
        self.calls.append((query, access))
        return self.hits[:limit]


class FakeRewriter:
    async def rewrite(
        self,
        query: str,
    ) -> list[str]:
        return [
            query,
            "VPN 无法连接怎么办？",
        ]


class IdentityReranker:
    async def rerank(
        self,
        query: str,
        candidates,
    ):
        del query
        return candidates


class StaticNormalizer:
    def __init__(self, values: list[str]) -> None:
        self.values = values

    def normalize(self, query: str) -> list[str]:
        del query
        return self.values


class StaticRewriter:
    def __init__(self, values: list[str]) -> None:
        self.values = values

    async def rewrite(self, query: str) -> list[str]:
        del query
        return self.values


class ConcurrentStore:
    def __init__(self, *, fail_queries: set[str] | None = None) -> None:
        self.fail_queries = fail_queries or set()
        self.calls: list[tuple[str, AccessContext, int]] = []
        self.active = 0
        self.maximum_active = 0

    async def search(
        self,
        query: str,
        access: AccessContext,
        limit: int = 5,
    ) -> list[VectorHit]:
        self.calls.append((query, access, limit))
        self.active += 1
        self.maximum_active = max(self.maximum_active, self.active)
        try:
            await asyncio.sleep(0.01)
            if query in self.fail_queries:
                raise RuntimeError(f"failed: {query}")
            return [
                VectorHit(
                    document_id=7,
                    filename="vpn.pdf",
                    page=3,
                    text="VPN 无法连接时先检查网络。",
                    score=0.8,
                    sensitivity="internal",
                )
            ]
        finally:
            self.active -= 1


@pytest.mark.asyncio
async def test_retrieval_uses_access_context() -> None:
    access = AccessContext(
        user_id=1,
        department="IT",
        roles=frozenset({"employee", "it_staff"}),
        knowledge_base_ids=frozenset({2}),
        dataset_ids=frozenset(),
    )
    store = FakeStore(
        [
            VectorHit(
                document_id=7,
                filename="vpn.pdf",
                page=3,
                text="先检查网络。",
                score=0.9,
                sensitivity="internal",
            )
        ]
    )
    service = RetrievalService(
        store=store,
        minimum_score=0.2,
    )

    citations = await service.search(
        "VPN 无法连接",
        access,
    )

    assert store.calls[0][1] == access
    assert citations[0].filename == "vpn.pdf"


@pytest.mark.asyncio
async def test_low_score_is_refused() -> None:
    access = AccessContext(
        1,
        "IT",
        frozenset({"it_staff"}),
        frozenset({2}),
        frozenset(),
    )
    store = FakeStore(
        [
            VectorHit(
                7,
                "vpn.pdf",
                3,
                "无关内容",
                0.1,
                "internal",
            )
        ]
    )
    service = RetrievalService(
        store,
        minimum_score=0.2,
    )

    assert (
        await service.search(
            "年假",
            access,
        )
        == []
    )


@pytest.mark.asyncio
async def test_enhanced_retrieval_reuses_same_access_context_for_all_queries() -> None:
    access = AccessContext(
        user_id=1,
        department="IT",
        roles=frozenset({"employee", "it_staff"}),
        knowledge_base_ids=frozenset({2}),
        dataset_ids=frozenset(),
    )
    store = FakeStore(
        [
            VectorHit(
                document_id=7,
                filename="vpn.pdf",
                page=3,
                text="VPN 无法连接时先检查网络。",
                score=0.5,
                sensitivity="internal",
            )
        ]
    )
    service = RetrievalService(
        store=store,
        minimum_score=0.2,
        rewriter=FakeRewriter(),
        reranker=IdentityReranker(),
    )

    result = await service.retrieve(
        "vpn没有连接怎么办？",
        access,
    )

    assert result.decision.citations
    assert len(store.calls) >= 2
    assert all(call_access == access for _, call_access in store.calls)
    assert "vpn无法连接怎么办？" in {query for query, _ in store.calls}


@pytest.mark.asyncio
async def test_queries_are_original_first_normalized_deduplicated_and_bounded() -> None:
    access = AccessContext(1, "IT", frozenset(), frozenset({2}), frozenset())
    store = ConcurrentStore()
    service = RetrievalService(
        store=store,
        minimum_score=0.2,
        normalizer=StaticNormalizer(
            [" vpn   help ", "VPN issue", "VPN route"]
        ),
        rewriter=StaticRewriter(
            ["VPN HELP", "VPN reset", "VPN extra"]
        ),
        reranker=IdentityReranker(),
        max_queries=4,
        recall_per_query=3,
    )

    result = await service.retrieve("VPN Help", access)

    assert result.queries == (
        "VPN Help",
        "VPN issue",
        "VPN route",
        "VPN reset",
    )
    assert len(store.calls) == 4
    assert all(limit == 3 for _, _, limit in store.calls)
    assert result.diagnostics["query_count"] == 4
    assert result.diagnostics["executed_queries"] == result.queries


@pytest.mark.asyncio
async def test_multi_query_searches_run_concurrently_and_share_access() -> None:
    access = AccessContext(1, "IT", frozenset(), frozenset({2}), frozenset())
    store = ConcurrentStore()
    service = RetrievalService(
        store=store,
        minimum_score=0.2,
        normalizer=StaticNormalizer(["q2", "q3"]),
        rewriter=StaticRewriter([]),
        reranker=IdentityReranker(),
        max_queries=4,
    )

    await service.retrieve("q1", access)

    assert store.maximum_active == 3
    assert all(call_access is access for _, call_access, _ in store.calls)


@pytest.mark.asyncio
async def test_one_query_failure_keeps_other_results() -> None:
    access = AccessContext(1, "IT", frozenset(), frozenset({2}), frozenset())
    store = ConcurrentStore(fail_queries={"broken"})
    service = RetrievalService(
        store=store,
        minimum_score=0.2,
        normalizer=StaticNormalizer(["broken", "working"]),
        rewriter=StaticRewriter([]),
        reranker=IdentityReranker(),
    )

    result = await service.retrieve("original", access)

    assert result.decision.citations
    assert result.diagnostics["successful_query_count"] == 2
    assert result.diagnostics["failed_query_count"] == 1


@pytest.mark.asyncio
async def test_all_query_failures_still_use_evidence_gate() -> None:
    access = AccessContext(1, "IT", frozenset(), frozenset({2}), frozenset())
    store = ConcurrentStore(fail_queries={"original", "broken"})
    service = RetrievalService(
        store=store,
        minimum_score=0.2,
        normalizer=StaticNormalizer(["broken"]),
        rewriter=StaticRewriter([]),
        reranker=IdentityReranker(),
    )

    result = await service.retrieve("original", access)

    assert result.decision.level == EvidenceLevel.INSUFFICIENT
    assert result.decision.citations == []
    assert result.diagnostics["successful_query_count"] == 0
    assert result.diagnostics["failed_query_count"] == 2
