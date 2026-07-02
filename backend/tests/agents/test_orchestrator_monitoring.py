import pytest

from app.agents.contracts import Sensitivity
from app.agents.orchestrator import AgentOrchestrator
from app.agents.router import RuleRouter
from app.knowledge.access import AccessContext
from app.knowledge.evidence_gate import EvidenceDecision, EvidenceLevel
from app.knowledge.retrieval import EnhancedRetrievalResult
from app.knowledge.schemas import Citation
from app.model_gateway.contracts import GatewayResponse
from app.monitoring.contracts import MonitorEvent

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
class RecordingMonitor:
    def __init__(self) -> None:
        self.events: list[MonitorEvent] = []

    def record(self, event: MonitorEvent) -> bool:
        self.events.append(event)
        return True


@pytest.mark.asyncio
async def test_question_keywords_do_not_create_simulated_monitor_warning() -> None:
    monitor = RecordingMonitor()
    orchestrator = AgentOrchestrator(
        router=RuleRouter(),
        gateway=FakeGateway(),
        retrieval=FakeRetrieval(),
        data_service=FakeDataService(),
        prompts=FakePromptResolver(),
        monitor=monitor,
    )

    result = await orchestrator.run(
        "模拟知识检索工具超时后的降级处理。",
        ACCESS,
    )

    assert "monitor_warning_detected" not in result.metadata
    assert "tool_timeout" not in result.metadata
    assert any(
        event.component == "orchestrator"
        and event.operation == "run"
        for event in monitor.events
    )
