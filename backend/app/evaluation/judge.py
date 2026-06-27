from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.agents.contracts import Sensitivity
from app.evaluation.contracts import CaseOutput, EvaluationCase
from app.model_gateway.contracts import ModelRequest
from app.model_gateway.gateway import ModelGateway

_DIMENSIONS = (
    "relevance",
    "accuracy",
    "completeness",
    "usefulness",
)


@dataclass(frozen=True)
class JudgeResult:
    enabled: bool
    available: bool
    scores: dict[str, float]
    overall_score: float
    reasons: list[str]
    improvement_suggestions: list[str]
    error: str | None = None
    provider: str | None = None
    model: str | None = None
    external_sent: bool = False


class LLMJudgeScorer:
    def __init__(
        self,
        gateway: ModelGateway,
        minimum_score: float = 0.75,
    ) -> None:
        self._gateway = gateway
        self._minimum_score = minimum_score

    async def score(
        self,
        case: EvaluationCase,
        output: CaseOutput,
    ) -> JudgeResult:
        if case.category == "safety" or case.judge_enabled is False:
            return JudgeResult(
                enabled=False,
                available=False,
                scores={},
                overall_score=0.0,
                reasons=[],
                improvement_suggestions=[],
            )

        sensitivity = self._judge_sensitivity(
            case,
            output,
        )
        try:
            response = await self._gateway.generate(
                ModelRequest(
                    system_prompt=self._system_prompt(),
                    user_message=self._user_message(
                        case,
                        output,
                    ),
                ),
                sensitivity,
            )
            payload = json.loads(response.text)
            scores = self._parse_scores(payload)
            overall = self._number(
                payload.get(
                    "overall_score",
                    sum(scores.values()) / len(scores),
                )
            )
            return JudgeResult(
                enabled=True,
                available=True,
                scores=scores,
                overall_score=overall,
                reasons=self._string_list(
                    payload.get("reasons", [])
                ),
                improvement_suggestions=self._string_list(
                    payload.get(
                        "improvement_suggestions",
                        [],
                    )
                ),
                provider=response.provider,
                model=response.model,
                external_sent=response.external_sent,
            )
        except Exception as exc:
            return JudgeResult(
                enabled=True,
                available=False,
                scores={name: 0.0 for name in _DIMENSIONS},
                overall_score=0.0,
                reasons=[],
                improvement_suggestions=[],
                error=str(exc)[:500],
            )

    @staticmethod
    def _judge_sensitivity(
        case: EvaluationCase,
        output: CaseOutput,
    ) -> Sensitivity:
        if (
            case.sensitivity == Sensitivity.PUBLIC.value
            and output.sensitivity == Sensitivity.PUBLIC.value
        ):
            return Sensitivity.PUBLIC
        return Sensitivity.SENSITIVE

    @staticmethod
    def _system_prompt() -> str:
        return (
            "你是企业知识助手评测裁判。请只返回 JSON，不要输出 Markdown。"
            "按 relevance、accuracy、completeness、usefulness 四个维度评分，"
            "每项为 0 到 1 的数字，并给出 overall_score、reasons、"
            "improvement_suggestions。"
        )

    @staticmethod
    def _user_message(
        case: EvaluationCase,
        output: CaseOutput,
    ) -> str:
        return json.dumps(
            {
                "case_id": case.case_id,
                "question": case.question,
                "expected_keywords": list(
                    case.expected_keywords
                ),
                "expected_citation": case.expected_citation,
                "answer": output.answer,
                "agent": output.agent,
                "provider": output.provider,
                "sensitivity": output.sensitivity,
                "refused": output.refused,
                "citations": list(output.citations),
            },
            ensure_ascii=False,
        )

    @staticmethod
    def _parse_scores(
        payload: dict[str, Any],
    ) -> dict[str, float]:
        return {
            name: LLMJudgeScorer._number(
                payload.get(name, 0.0)
            )
            for name in _DIMENSIONS
        }

    @staticmethod
    def _number(value: object) -> float:
        if isinstance(value, int | float | str):
            try:
                parsed = float(value)
            except ValueError:
                parsed = 0.0
        else:
            parsed = 0.0
        return min(
            1.0,
            max(0.0, parsed),
        )

    @staticmethod
    def _string_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value]
