import pytest

from app.agents.contracts import AgentType, Sensitivity
from app.agents.orchestrator import AgentOrchestrator
from app.agents.router import RuleRouter
from app.knowledge.access import AccessContext
from app.knowledge.evidence_gate import EvidenceDecision, EvidenceLevel
from app.knowledge.retrieval import EnhancedRetrievalResult
from app.knowledge.schemas import Citation
from app.model_gateway.contracts import GatewayResponse

ACCESS = AccessContext(
    user_id=1,
    department="IT",
    roles=frozenset({"employee", "it_staff"}),
    knowledge_base_ids=frozenset({1}),
    dataset_ids=frozenset(),
)


class FakeRetrieval:
    async def retrieve(
        self,
        query: str,
        access: AccessContext,
        limit: int = 5,
    ) -> EnhancedRetrievalResult:
        del query, access, limit
        return EnhancedRetrievalResult(
            queries=("vpn",),
            candidates=(),
            decision=EvidenceDecision(
                level=EvidenceLevel.FULL,
                citations=[
                    Citation(
                        document_id=1,
                        filename="vpn.md",
                        page=1,
                        text="VPN 无法连接时先检查网络。",
                        score=0.9,
                        sensitivity="internal",
                    )
                ],
            ),
        )


class FakeGateway:
    async def generate(
        self,
        request,
        sensitivity: Sensitivity,
    ) -> GatewayResponse:
        del request, sensitivity
        return GatewayResponse(
            text="VPN 排查步骤：检查网络和账号。",
            model="fake",
            provider="ollama",
            route_reason="test",
            external_sent=False,
        )


class DeniedDataService:
    async def answer(
        self,
        question: str,
        access: AccessContext,
        memory_context: str = "",
    ):
        del question, access, memory_context
        raise PermissionError


class FakePromptResolver:
    async def resolve(
        self,
        prompt_key: str,
        fallback: str,
    ) -> str:
        del prompt_key
        return fallback


@pytest.mark.asyncio
async def test_orchestrator_returns_partial_success_for_composite_question() -> None:
    orchestrator = AgentOrchestrator(
        router=RuleRouter(),
        gateway=FakeGateway(),
        retrieval=FakeRetrieval(),
        data_service=DeniedDataService(),
        prompts=FakePromptResolver(),
        composite_enabled=True,
    )

    result = await orchestrator.run(
        "先说明 VPN 无法连接的排查步骤，再统计最近 7 天 IT 工单数量。",
        ACCESS,
    )

    assert result.agent is AgentType.IT
    assert result.refused is False
    assert result.external_sent is False
    assert result.metadata["composite"] is True
    assert result.metadata["partial_success"] is True
    assert "VPN" in result.answer
    assert "工单统计" in result.answer
