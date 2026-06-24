import pytest

from app.knowledge.access import AccessContext
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
    assert "VPN 无法连接怎么办？" in {query for query, _ in store.calls}
