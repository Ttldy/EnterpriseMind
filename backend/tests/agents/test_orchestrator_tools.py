import pytest

from app.agents.contracts import AgentType, Sensitivity
from app.agents.orchestrator import AgentOrchestrator
from app.agents.router import RuleRouter
from app.knowledge.access import AccessContext
from app.knowledge.evidence_gate import EvidenceDecision, EvidenceLevel
from app.knowledge.retrieval import EnhancedRetrievalResult
from app.knowledge.schemas import Citation
from app.model_gateway.contracts import GatewayResponse
from app.tools.contracts import ToolResult

ACCESS = AccessContext(
    user_id=1,
    department="IT",
    roles=frozenset({"employee", "it_staff"}),
    knowledge_base_ids=frozenset({1}),
    dataset_ids=frozenset(),
)


class UnusedRetrieval:
    async def retrieve(
        self,
        query: str,
        access: AccessContext,
        limit: int = 5,
    ) -> EnhancedRetrievalResult:
        del query, access, limit
        raise AssertionError("tool manager should run retrieval")


class FallbackRetrieval:
    async def retrieve(
        self,
        query: str,
        access: AccessContext,
        limit: int = 5,
    ) -> EnhancedRetrievalResult:
        del query, access, limit
        return full_result()


class SuccessfulToolManager:
    async def execute(
        self,
        name: str,
        payload: dict[str, object],
        context,
    ) -> ToolResult:
        assert name == "knowledge_search"
        assert payload["query"] == "vpn没有连接怎么办？"
        assert context.user_id == 1
        return ToolResult(
            success=True,
            output=full_result(),
            metadata={
                "tool_success": True,
                "tool_name": "knowledge_search",
            },
        )


class FailingToolManager:
    async def execute(
        self,
        name: str,
        payload: dict[str, object],
        context,
    ) -> ToolResult:
        del name, payload, context
        return ToolResult(
            success=False,
            output=None,
            metadata={
                "tool_success": False,
                "tool_fallback": True,
            },
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


def full_result() -> EnhancedRetrievalResult:
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


@pytest.mark.asyncio
async def test_orchestrator_uses_tool_manager_for_knowledge_search() -> None:
    orchestrator = AgentOrchestrator(
        router=RuleRouter(),
        gateway=FakeGateway(),
        retrieval=UnusedRetrieval(),
        data_service=FakeDataService(),
        prompts=FakePromptResolver(),
        tool_manager=SuccessfulToolManager(),
    )

    result = await orchestrator.run(
        "vpn没有连接怎么办？",
        ACCESS,
    )

    assert result.agent is AgentType.IT
    assert result.metadata["tool_success"] is True
    assert result.metadata["tool_name"] == "knowledge_search"


@pytest.mark.asyncio
async def test_orchestrator_falls_back_when_tool_manager_fails() -> None:
    orchestrator = AgentOrchestrator(
        router=RuleRouter(),
        gateway=FakeGateway(),
        retrieval=FallbackRetrieval(),
        data_service=FakeDataService(),
        prompts=FakePromptResolver(),
        tool_manager=FailingToolManager(),
    )

    result = await orchestrator.run(
        "vpn没有连接怎么办？",
        ACCESS,
    )

    assert result.agent is AgentType.IT
    assert result.metadata["tool_success"] is False
    assert result.metadata["tool_fallback"] is True
