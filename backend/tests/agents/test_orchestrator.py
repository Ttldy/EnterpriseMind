import pytest

from app.agents.contracts import (
    AgentType,
    Sensitivity,
)
from app.agents.orchestrator import (
    AgentOrchestrator,
)
from app.agents.router import RuleRouter
from app.knowledge.access import AccessContext
from app.knowledge.schemas import Citation
from app.model_gateway.contracts import (
    GatewayResponse,
)

ACCESS = AccessContext(
    user_id=1,
    department="IT",
    roles=frozenset({"employee", "it_staff"}),
    knowledge_base_ids=frozenset({1}),
    dataset_ids=frozenset(),
)


class FakeRetrieval:
    def __init__(
        self,
        citations: list[Citation],
    ) -> None:
        self.citations = citations

    async def search(
        self,
        query: str,
        access: AccessContext,
        limit: int = 5,
    ) -> list[Citation]:
        return self.citations[:limit]


class FakeGateway:
    def __init__(self) -> None:
        self.sensitivities: list[Sensitivity] = []

    async def generate(
        self,
        request,
        sensitivity: Sensitivity,
    ) -> GatewayResponse:
        self.sensitivities.append(sensitivity)
        return GatewayResponse(
            text="fake answer",
            model="fake-model",
            provider="ollama",
            route_reason=(f"{sensitivity.value}_requires_local"),
            external_sent=False,
        )


class FakeDataService:
    async def answer(
        self,
        question: str,
        access: AccessContext,
    ):
        raise PermissionError


@pytest.mark.asyncio
async def test_internal_evidence_uses_local() -> None:
    gateway = FakeGateway()
    orchestrator = AgentOrchestrator(
        router=RuleRouter(),
        gateway=gateway,
        retrieval=FakeRetrieval(
            [
                Citation(
                    document_id=1,
                    filename="vpn.md",
                    page=1,
                    text="先检查网络。",
                    score=0.9,
                    sensitivity="internal",
                )
            ]
        ),
        data_service=FakeDataService(),
    )

    result = await orchestrator.run(
        "VPN 无法连接怎么办？",
        ACCESS,
    )

    assert result.agent is AgentType.IT
    assert result.provider == "ollama"
    assert result.external_sent is False
    assert gateway.sensitivities == [Sensitivity.INTERNAL]


@pytest.mark.asyncio
async def test_no_evidence_refuses() -> None:
    gateway = FakeGateway()
    orchestrator = AgentOrchestrator(
        router=RuleRouter(),
        gateway=gateway,
        retrieval=FakeRetrieval([]),
        data_service=FakeDataService(),
    )

    result = await orchestrator.run(
        "VPN 无法连接怎么办？",
        ACCESS,
    )

    assert result.refused is True
    assert result.model == "none"
    assert gateway.sensitivities == []


@pytest.mark.asyncio
async def test_unauthorized_data_query_refuses() -> None:
    orchestrator = AgentOrchestrator(
        router=RuleRouter(),
        gateway=FakeGateway(),
        retrieval=FakeRetrieval([]),
        data_service=FakeDataService(),
    )

    result = await orchestrator.run(
        "统计各部门报销金额",
        ACCESS,
    )

    assert result.agent is AgentType.DATA_ANALYST
    assert result.refused is True
    assert result.external_sent is False
    assert result.sql is None
