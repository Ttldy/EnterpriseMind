from dataclasses import dataclass
from enum import StrEnum

from app.knowledge.fusion import FusedHit
from app.knowledge.schemas import Citation


class EvidenceLevel(StrEnum):
    FULL = "full"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class EvidenceDecision:
    level: EvidenceLevel
    citations: list[Citation]
    notice: str = ""


class EvidenceGate:
    def __init__(
        self,
        full_answer_score: float,
        partial_answer_score: float,
        minimum_hit_count: int,
    ) -> None:
        self._full_answer_score = full_answer_score
        self._partial_answer_score = partial_answer_score
        self._minimum_hit_count = minimum_hit_count

    def evaluate(
        self,
        query: str,
        candidates: list[FusedHit],
    ) -> EvidenceDecision:
        del query
        usable = [
            item
            for item in candidates
            if item.best_score >= self._partial_answer_score
        ]
        if not usable:
            return EvidenceDecision(
                level=EvidenceLevel.INSUFFICIENT,
                citations=[],
                notice="当前有权限访问的知识库中没有足够证据回答该问题。",
            )

        top = usable[0]
        citations = [
            Citation(
                document_id=item.hit.document_id,
                filename=item.hit.filename,
                page=item.hit.page,
                text=item.hit.text,
                score=item.best_score,
                sensitivity=item.hit.sensitivity,
            )
            for item in usable
        ]
        if (
            top.best_score >= self._full_answer_score
            and top.hit_count >= self._minimum_hit_count
        ):
            return EvidenceDecision(
                level=EvidenceLevel.FULL,
                citations=citations,
            )

        return EvidenceDecision(
            level=EvidenceLevel.PARTIAL,
            citations=citations,
            notice="证据有限，以下回答只基于当前可访问知识库中的相关片段。",
        )
