import json
from dataclasses import replace
from typing import Protocol

from app.agents.contracts import Sensitivity
from app.knowledge.fusion import FusedHit
from app.model_gateway.contracts import GatewayResponse, ModelRequest


class RerankGateway(Protocol):
    async def generate(
        self,
        request: ModelRequest,
        sensitivity: Sensitivity,
    ) -> GatewayResponse: ...


class SensitiveAwareReranker:
    def __init__(
        self,
        gateway: RerankGateway,
        maximum_candidates: int = 8,
        maximum_text_chars: int = 500,
    ) -> None:
        self._gateway = gateway
        self._maximum_candidates = maximum_candidates
        self._maximum_text_chars = maximum_text_chars

    async def rerank(
        self,
        query: str,
        candidates: list[FusedHit],
    ) -> list[FusedHit]:
        if not candidates:
            return []

        limited = candidates[: self._maximum_candidates]
        sensitivity = _highest_candidate_sensitivity(limited)
        prompt = (
            "你是企业知识库 RAG 重排器。"
            "请判断每条候选证据是否能直接支持回答问题。"
            "只返回 JSON 数组，每项格式为 "
            "{\"index\": 1, \"relevance\": 0.0, "
            "\"coverage\": 0.0, \"reason\": \"简短理由\"}。"
            "relevance 表示相关性，coverage 表示对问题所需信息的覆盖度，"
            "均必须在 0 到 1 之间。不得补充候选中不存在的事实。"
        )
        candidate_text = "\n\n".join(
            (
                f"[{index}] score={item.best_score:.4f} "
                f"hits={item.hit_count}\n"
                f"{item.hit.text[: self._maximum_text_chars]}"
            )
            for index, item in enumerate(
                limited,
                start=1,
            )
        )
        try:
            response = await self._gateway.generate(
                ModelRequest(
                    system_prompt=prompt,
                    user_message=(
                        f"问题：{query}\n\n候选证据：\n{candidate_text}"
                    ),
                ),
                sensitivity,
            )
            payload = json.loads(response.text)
        except Exception:
            return _fallback(candidates)

        raw_items = (
            payload.get("items")
            if isinstance(payload, dict)
            else payload
        )
        scores: dict[int, tuple[float, float, str]] = {}
        if isinstance(raw_items, list):
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                index = item.get("index")
                relevance = item.get("relevance", item.get("score"))
                coverage = item.get("coverage", relevance)
                if (
                    isinstance(index, int)
                    and isinstance(relevance, int | float)
                    and isinstance(coverage, int | float)
                ):
                    scores[index] = (
                        _score(relevance),
                        _score(coverage),
                        str(item.get("reason", ""))[:200],
                    )

        if not scores:
            return _fallback(candidates)

        annotated: list[FusedHit] = []
        for index, item in enumerate(limited, start=1):
            relevance, coverage, reason = scores.get(
                index,
                _fallback_values(item),
            )
            annotated.append(
                replace(
                    item,
                    relevance=relevance,
                    coverage=coverage,
                    rerank_reason=reason,
                )
            )
        reranked = sorted(
            annotated,
            key=lambda item: (
                item.relevance or 0.0,
                item.coverage or 0.0,
                item.fused_score,
            ),
            reverse=True,
        )
        return reranked + _fallback(candidates[self._maximum_candidates :])


class ScoreReranker:
    async def rerank(
        self,
        query: str,
        candidates: list[FusedHit],
    ) -> list[FusedHit]:
        del query
        return _fallback(candidates)


def _fallback(
    candidates: list[FusedHit],
) -> list[FusedHit]:
    return [
        replace(
            item,
            relevance=_fallback_values(item)[0],
            coverage=_fallback_values(item)[1],
            rerank_reason=_fallback_values(item)[2],
        )
        for item in candidates
    ]


def _fallback_values(
    candidate: FusedHit,
) -> tuple[float, float, str]:
    return (
        _score(candidate.best_score),
        min(1.0, candidate.hit_count / 2),
        "deterministic_fallback",
    )


def _score(value: int | float) -> float:
    return max(0.0, min(1.0, float(value)))


def _highest_candidate_sensitivity(
    candidates: list[FusedHit],
) -> Sensitivity:
    values = {item.hit.sensitivity.lower() for item in candidates}
    if "sensitive" in values:
        return Sensitivity.SENSITIVE
    if "internal" in values:
        return Sensitivity.INTERNAL
    return Sensitivity.PUBLIC
