from app.knowledge.evidence_gate import (
    EvidenceGate,
    EvidenceLevel,
)
from app.knowledge.fusion import FusedHit
from app.knowledge.vector_store import VectorHit


def fused(
    score: float,
    hit_count: int = 1,
    text: str = "VPN 无法连接时先检查网络，再确认账号状态。",
) -> FusedHit:
    return FusedHit(
        hit=VectorHit(
            document_id=1,
            filename="vpn.md",
            page=1,
            text=text,
            score=score,
            sensitivity="internal",
        ),
        best_score=score,
        hit_count=hit_count,
        fused_score=score + hit_count * 0.05,
        source_queries=("vpn无法连接怎么办？",),
    )


def test_gate_allows_full_answer_when_score_and_hits_are_strong() -> None:
    gate = EvidenceGate(
        full_answer_score=0.45,
        partial_answer_score=0.25,
        minimum_hit_count=2,
    )

    decision = gate.evaluate("vpn没有连接怎么办？", [fused(0.48, 2)])

    assert decision.level is EvidenceLevel.FULL
    assert decision.citations[0].filename == "vpn.md"


def test_gate_allows_partial_answer_with_boundary_notice() -> None:
    gate = EvidenceGate(
        full_answer_score=0.45,
        partial_answer_score=0.25,
        minimum_hit_count=2,
    )

    decision = gate.evaluate("vpn没有连接怎么办？", [fused(0.3, 1)])

    assert decision.level is EvidenceLevel.PARTIAL
    assert "证据有限" in decision.notice


def test_gate_refuses_when_evidence_is_weak() -> None:
    gate = EvidenceGate(
        full_answer_score=0.45,
        partial_answer_score=0.25,
        minimum_hit_count=2,
    )

    decision = gate.evaluate("火星基地在哪里？", [fused(0.12, 1, "无关内容")])

    assert decision.level is EvidenceLevel.INSUFFICIENT
    assert decision.citations == []
