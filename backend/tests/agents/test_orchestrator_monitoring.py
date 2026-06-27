import pytest

from app.agents.contracts import Sensitivity
from app.agents.orchestrator import AgentOrchestrator
from app.agents.router import RuleRouter
from app.knowledge.access import AccessContext
from app.knowledge.evidence_gate import EvidenceDecision, EvidenceLevel
from app.knowledge.retrieval import EnhancedRetrievalResult
from app.knowledge.schemas import Citation
from app.model_gateway.contracts import GatewayResponse
from app.monitoring.service import MonitoringService

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
            text="fake answer",
            model="fake",
            provider="ollama",
            route_reason="test",
            external_sent=False,
        )


class FakeDataService:
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
async def test_orchestrator_adds_monitor_warning_metadata() -> None:
    orchestrator = AgentOrchestrator(
        router=RuleRouter(),
        gateway=FakeGateway(),
        retrieval=FakeRetrieval(),
        data_service=FakeDataService(),
        prompts=FakePromptResolver(),
        monitor=MonitoringService(),
    )

    result = await orchestrator.run(
        "模拟知识检索工具超时后的降级处理。",
        ACCESS,
    )

    assert result.metadata["monitor_warning_detected"] is True
    assert result.metadata["monitor_reason"] == "simulated_timeout"
