from app.knowledge.fusion import fuse_hits
from app.knowledge.vector_store import VectorHit


def hit(
    document_id: int,
    page: int,
    text: str,
    score: float,
) -> VectorHit:
    return VectorHit(
        document_id=document_id,
        filename=f"doc-{document_id}.md",
        page=page,
        text=text,
        score=score,
        sensitivity="internal",
    )


def test_fusion_deduplicates_same_chunk_and_counts_hits() -> None:
    fused = fuse_hits(
        [
            ("vpn没有连接怎么办？", [hit(1, 1, "检查网络和账号", 0.34)]),
            ("vpn无法连接怎么办？", [hit(1, 1, "检查网络和账号", 0.42)]),
        ],
        limit=5,
    )

    assert len(fused) == 1
    assert fused[0].hit_count == 2
    assert fused[0].best_score == 0.42
    assert fused[0].source_queries == (
        "vpn没有连接怎么办？",
        "vpn无法连接怎么办？",
    )


def test_fusion_prioritizes_score_and_multiple_hits() -> None:
    fused = fuse_hits(
        [
            ("q1", [hit(1, 1, "A", 0.35), hit(2, 1, "B", 0.38)]),
            ("q2", [hit(1, 1, "A", 0.33)]),
        ],
        limit=2,
    )

    assert [item.hit.document_id for item in fused] == [1, 2]
