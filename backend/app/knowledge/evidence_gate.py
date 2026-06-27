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
        full_relevance_score: float | None = None,
        full_coverage_score: float = 0.0,
        partial_relevance_score: float | None = None,
        partial_vector_score: float | None = None,
        final_top_k: int = 5,
    ) -> None:
        self._full_answer_score = full_answer_score
        self._partial_answer_score = partial_answer_score
        self._minimum_hit_count = minimum_hit_count
        self._full_relevance_score = (
            full_answer_score
            if full_relevance_score is None
            else full_relevance_score
        )
        self._full_coverage_score = full_coverage_score
        self._partial_relevance_score = (
            partial_answer_score
            if partial_relevance_score is None
            else partial_relevance_score
        )
        self._partial_vector_score = (
            partial_answer_score
            if partial_vector_score is None
            else partial_vector_score
        )
        self._final_top_k = final_top_k

    def evaluate(
        self,
        query: str,
        candidates: list[FusedHit],
    ) -> EvidenceDecision:
        del query
        usable = [
            item
            for item in candidates
            if (
                _relevance(item) >= self._partial_relevance_score
                and item.best_score >= self._partial_vector_score
            )
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
            for item in usable[: self._final_top_k]
        ]
        if (
            top.best_score >= self._full_answer_score
            and _relevance(top) >= self._full_relevance_score
            and _coverage(top) >= self._full_coverage_score
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


def _relevance(candidate: FusedHit) -> float:
    if candidate.relevance is not None:
        return candidate.relevance
    return max(0.0, min(1.0, candidate.best_score))


def _coverage(candidate: FusedHit) -> float:
    if candidate.coverage is not None:
        return candidate.coverage
    return min(1.0, candidate.hit_count / 2)
