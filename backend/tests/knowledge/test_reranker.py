import pytest

from app.knowledge.fusion import FusedHit
from app.knowledge.reranker import SensitiveAwareReranker
from app.knowledge.vector_store import VectorHit
from app.model_gateway.contracts import GatewayResponse


def candidate(
    *,
    text: str,
    score: float,
) -> FusedHit:
    return FusedHit(
        hit=VectorHit(
            document_id=1,
            filename="policy.md",
            page=1,
            text=text,
            score=score,
            sensitivity="public",
        ),
        best_score=score,
        hit_count=1,
        fused_score=score,
        source_queries=("年假怎么申请",),
    )


class JsonGateway:
    async def generate(self, request, sensitivity):
        del request, sensitivity
        return GatewayResponse(
            text=(
                '[{"index": 1, "relevance": 0.08, '
                '"coverage": 0.0, "reason": "不包含年假制度"}]'
            ),
            provider="demo",
            model="judge",
            route_reason="test",
            external_sent=False,
        )


class BrokenGateway:
    async def generate(self, request, sensitivity):
        del request, sensitivity
        raise RuntimeError("reranker unavailable")


@pytest.mark.asyncio
async def test_reranker_attaches_relevance_and_coverage() -> None:
    reranker = SensitiveAwareReranker(JsonGateway())

    result = await reranker.rerank(
        "年假怎么申请",
        [candidate(text="公司办公时间为 9:00 至 18:00。", score=0.45)],
    )

    assert result[0].relevance == 0.08
    assert result[0].coverage == 0.0
    assert result[0].rerank_reason == "不包含年假制度"


@pytest.mark.asyncio
async def test_reranker_failure_uses_deterministic_vector_fallback() -> None:
    reranker = SensitiveAwareReranker(BrokenGateway())

    result = await reranker.rerank(
        "年假怎么申请",
        [candidate(text="公司办公时间为 9:00 至 18:00。", score=0.45)],
    )

    assert result[0].relevance == 0.45
    assert result[0].coverage == 0.5
    assert result[0].rerank_reason == "deterministic_fallback"
