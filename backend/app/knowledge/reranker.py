import json
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
            "请根据问题和候选证据相关性返回 JSON 数组，"
            "每项格式为 {\"index\": 1, \"score\": 0.0 到 1.0}。"
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
            return candidates

        scores: dict[int, float] = {}
        if isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict):
                    continue
                index = item.get("index")
                score = item.get("score")
                if isinstance(index, int) and isinstance(score, int | float):
                    scores[index] = float(score)

        if not scores:
            return candidates

        reranked = sorted(
            enumerate(
                limited,
                start=1,
            ),
            key=lambda pair: (
                scores.get(pair[0], 0.0),
                pair[1].fused_score,
            ),
            reverse=True,
        )
        return [item for _, item in reranked] + candidates[self._maximum_candidates :]


class ScoreReranker:
    async def rerank(
        self,
        query: str,
        candidates: list[FusedHit],
    ) -> list[FusedHit]:
        del query
        return candidates


def _highest_candidate_sensitivity(
    candidates: list[FusedHit],
) -> Sensitivity:
    values = {item.hit.sensitivity.lower() for item in candidates}
    if "sensitive" in values:
        return Sensitivity.SENSITIVE
    if "internal" in values:
        return Sensitivity.INTERNAL
    return Sensitivity.PUBLIC
