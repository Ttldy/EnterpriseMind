import pytest

from app.agents.contracts import AgentType
from app.agents.orchestrator import AgentOrchestrator
from app.agents.router import RuleRouter
from app.model_gateway.contracts import ModelRequest, ModelResponse


class FakeProvider:
    def __init__(self) -> None:
        self.last_request: ModelRequest | None = None

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.last_request = request
        return ModelResponse(
            text=f"fake answer: {request.user_message}",
            model="fake-model",
        )


@pytest.mark.asyncio
async def test_orchestrator_selects_hr_prompt() -> None:
    provider = FakeProvider()
    orchestrator = AgentOrchestrator(
        router=RuleRouter(),
        provider=provider,
    )

    result = await orchestrator.run("年假有几天？")

    assert result.agent is AgentType.HR
    assert result.model == "fake-model"
    assert provider.last_request is not None
    assert "人事制度助手" in provider.last_request.system_prompt


@pytest.mark.asyncio
async def test_orchestrator_returns_clarification_without_calling_model() -> None:
    provider = FakeProvider()
    orchestrator = AgentOrchestrator(
        router=RuleRouter(),
        provider=provider,
    )

    result = await orchestrator.run("帮我看看这个")

    assert result.agent is AgentType.CLARIFICATION
    assert result.model == "none"
    assert provider.last_request is None
    assert "补充" in result.answer