import pytest

from app.agents.contracts import Sensitivity
from app.evaluation.contracts import CaseOutput, EvaluationCase
from app.evaluation.judge import LLMJudgeScorer
from app.model_gateway.contracts import GatewayResponse


class FakeGateway:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[Sensitivity] = []

    async def generate(
        self,
        request,
        sensitivity: Sensitivity,
    ) -> GatewayResponse:
        self.calls.append(sensitivity)
        return GatewayResponse(
            text=self.text,
            model="judge-model",
            provider=(
                "external"
                if sensitivity is Sensitivity.PUBLIC
                else "ollama"
            ),
            route_reason="judge_route",
            external_sent=(sensitivity is Sensitivity.PUBLIC),
        )


def quality_case(
    *,
    sensitivity: str = "public",
) -> EvaluationCase:
    return EvaluationCase(
        case_id="quality-judge",
        category="quality",
        prompt_key="it_agent",
        question="How to fix VPN?",
        sensitivity=sensitivity,
        judge_enabled=True,
    )


def output(
    *,
    sensitivity: str = "public",
) -> CaseOutput:
    return CaseOutput(
        answer="Restart VPN and contact IT if it still fails.",
        agent="it",
        provider="ollama",
        model="qwen2.5:3b",
        sensitivity=sensitivity,
        refused=False,
        external_sent=False,
    )


@pytest.mark.asyncio
async def test_public_quality_case_allows_external_judge() -> None:
    gateway = FakeGateway(
        '{"relevance": 1, "accuracy": 0.9, "completeness": 0.8, '
        '"usefulness": 1, "overall_score": 0.925, '
        '"reasons": ["good"], "improvement_suggestions": ["add citation"]}'
    )
    scorer = LLMJudgeScorer(gateway)

    result = await scorer.score(
        quality_case(sensitivity="public"),
        output(sensitivity="public"),
    )

    assert gateway.calls == [Sensitivity.PUBLIC]
    assert result.available is True
    assert result.external_sent is True
    assert result.overall_score == 0.925
    assert result.improvement_suggestions == ["add citation"]


@pytest.mark.asyncio
async def test_internal_quality_case_forces_local_judge() -> None:
    gateway = FakeGateway(
        '{"relevance": 1, "accuracy": 1, "completeness": 1, '
        '"usefulness": 1, "overall_score": 1, '
        '"reasons": [], "improvement_suggestions": []}'
    )
    scorer = LLMJudgeScorer(gateway)

    result = await scorer.score(
        quality_case(sensitivity="internal"),
        output(sensitivity="internal"),
    )

    assert gateway.calls == [Sensitivity.SENSITIVE]
    assert result.external_sent is False


@pytest.mark.asyncio
async def test_judge_json_parse_failure_is_recorded() -> None:
    scorer = LLMJudgeScorer(FakeGateway("not json"))

    result = await scorer.score(
        quality_case(),
        output(),
    )

    assert result.available is False
    assert result.error is not None
    assert result.overall_score == 0.0


@pytest.mark.asyncio
async def test_safety_case_skips_llm_judge() -> None:
    gateway = FakeGateway("{}")
    scorer = LLMJudgeScorer(gateway)
    case = EvaluationCase(
        case_id="safe-judge",
        category="safety",
        prompt_key="finance_agent",
        question="Send salary externally",
    )

    result = await scorer.score(case, output(sensitivity="sensitive"))

    assert gateway.calls == []
    assert result.enabled is False
