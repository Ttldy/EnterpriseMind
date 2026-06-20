import pytest

from app.agents.contracts import AgentType
from app.agents.orchestrator import AgentOrchestrator
from app.agents.router import RuleRouter
from app.knowledge.access import AccessContext
from app.knowledge.schemas import Citation
from app.model_gateway.contracts import (
    ModelRequest,
    ModelResponse,
)


class FakeProvider:
    def __init__(self) -> None:
        self.last_request: ModelRequest | None = None

    async def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        self.last_request = request
        return ModelResponse(
            text=f"fake answer: {request.user_message}",
            model="fake-model",
        )


class FakeRetrieval:
    def __init__(
        self,
        citations: list[Citation],
    ) -> None:
        self.citations = citations
        self.last_access: AccessContext | None = None

    async def search(
        self,
        query: str,
        access: AccessContext,
        limit: int = 5,
    ) -> list[Citation]:
        self.last_access = access
        return self.citations[:limit]


ACCESS = AccessContext(
    user_id=1,
    department="IT",
    roles=frozenset({"employee"}),
    knowledge_base_ids=frozenset({1}),
    dataset_ids=frozenset(),
)


@pytest.mark.asyncio
async def test_orchestrator_selects_hr_prompt() -> None:
    provider = FakeProvider()
    retrieval = FakeRetrieval(
        [
            Citation(
                document_id=1,
                filename="员工手册.pdf",
                page=3,
                text="正式员工每年享有带薪年假。",
                score=0.9,
                sensitivity="internal",
            )
        ]
    )
    orchestrator = AgentOrchestrator(
        router=RuleRouter(),
        provider=provider,
        retrieval=retrieval,
    )

    result = await orchestrator.run(
        "年假有几天？",
        ACCESS,
    )

    assert result.agent is AgentType.HR
    assert result.model == "fake-model"
    assert provider.last_request is not None
    assert "人事制度助手" in (provider.last_request.system_prompt)
    assert "员工手册.pdf" in (provider.last_request.system_prompt)
    assert retrieval.last_access == ACCESS


@pytest.mark.asyncio
async def test_orchestrator_refuses_without_evidence() -> None:
    provider = FakeProvider()
    orchestrator = AgentOrchestrator(
        router=RuleRouter(),
        provider=provider,
        retrieval=FakeRetrieval([]),
    )

    result = await orchestrator.run(
        "年假有几天？",
        ACCESS,
    )

    assert result.refused is True
    assert result.model == "none"
    assert provider.last_request is None


@pytest.mark.asyncio
async def test_clarification_does_not_call_model() -> None:
    provider = FakeProvider()
    orchestrator = AgentOrchestrator(
        router=RuleRouter(),
        provider=provider,
        retrieval=FakeRetrieval([]),
    )

    result = await orchestrator.run(
        "帮我看看这个",
        ACCESS,
    )

    assert result.agent is AgentType.CLARIFICATION
    assert result.model == "none"
    assert provider.last_request is None
    assert "补充" in result.answer
