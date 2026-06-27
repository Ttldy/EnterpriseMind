import json

import pytest

from app.agents.contracts import (
    AgentType,
    IntentType,
    Sensitivity,
)
from app.agents.intent_recognizer import (
    EnterpriseIntentRecognizer,
)
from app.model_gateway.contracts import GatewayResponse


class FakeEmbedding:
    dimensions = 3

    async def embed(self, text: str) -> list[float]:
        normalized = text.lower()
        if "内网" in normalized or "电脑" in normalized:
            return [1.0, 0.0, 0.0]
        if "报销" in normalized:
            return [0.0, 1.0, 0.0]
        if "考勤" in normalized:
            return [0.0, 0.0, 1.0]
        return [0.0, 0.0, 0.0]


class FailingEmbedding:
    dimensions = 3

    async def embed(self, text: str) -> list[float]:
        del text
        raise RuntimeError("embedding unavailable")


class FakeGateway:
    def __init__(
        self,
        payload: dict[str, object],
    ) -> None:
        self.payload = payload
        self.sensitivities: list[Sensitivity] = []

    async def generate(
        self,
        request,
        sensitivity: Sensitivity,
    ) -> GatewayResponse:
        del request
        self.sensitivities.append(sensitivity)
        return GatewayResponse(
            text=json.dumps(
                self.payload,
                ensure_ascii=False,
            ),
            model="fake",
            provider="ollama",
            route_reason="test",
            external_sent=False,
        )


@pytest.mark.asyncio
async def test_hybrid_recognizer_routes_unsafe_sql_to_data_analyst() -> None:
    recognizer = EnterpriseIntentRecognizer()

    result = await recognizer.route("帮我执行 DELETE FROM reimbursements")

    assert result.agent is AgentType.DATA_ANALYST
    assert result.intent is IntentType.DATA_QUERY
    assert result.requires_sql is True
    assert result.sensitivity is Sensitivity.SENSITIVE


@pytest.mark.asyncio
async def test_hybrid_recognizer_uses_embedding_when_pattern_is_unclear() -> None:
    recognizer = EnterpriseIntentRecognizer(
        embedding=FakeEmbedding(),
        gateway=None,
    )

    result = await recognizer.route("电脑连不上公司内网怎么办")

    assert result.agent is AgentType.IT
    assert result.intent is IntentType.KNOWLEDGE_QUERY
    assert result.confidence >= 0.5


@pytest.mark.asyncio
async def test_hybrid_recognizer_uses_llm_when_pattern_and_embedding_are_unclear() -> None:
    gateway = FakeGateway(
        {
            "agent": "finance",
            "intent": "knowledge_query",
            "requires_sql": False,
            "sensitivity": "internal",
            "confidence": 0.82,
        }
    )
    recognizer = EnterpriseIntentRecognizer(
        embedding=FailingEmbedding(),
        gateway=gateway,
    )

    result = await recognizer.route("供应商付款流程怎么看")

    assert result.agent is AgentType.FINANCE
    assert result.intent is IntentType.KNOWLEDGE_QUERY
    assert result.requires_sql is False
    assert result.sensitivity is Sensitivity.INTERNAL


@pytest.mark.asyncio
async def test_hybrid_recognizer_sends_sensitive_intent_judgment_to_local_model() -> None:
    gateway = FakeGateway(
        {
            "agent": "data_analyst",
            "intent": "data_query",
            "requires_sql": True,
            "sensitivity": "sensitive",
            "confidence": 0.9,
        }
    )
    recognizer = EnterpriseIntentRecognizer(
        embedding=FailingEmbedding(),
        gateway=gateway,
    )

    await recognizer.route("手机号字段的查询口径应该怎么看")

    assert gateway.sensitivities == [Sensitivity.SENSITIVE]
