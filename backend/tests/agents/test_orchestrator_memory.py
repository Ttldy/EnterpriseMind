import pytest

from app.agents.contracts import Sensitivity
from app.agents.orchestrator import AgentOrchestrator
from app.agents.router import RuleRouter
from app.knowledge.access import AccessContext
from app.knowledge.evidence_gate import EvidenceDecision, EvidenceLevel
from app.knowledge.retrieval import EnhancedRetrievalResult
from app.knowledge.schemas import Citation
from app.model_gateway.contracts import GatewayResponse

ACCESS = AccessContext(
    user_id=7,
    department="IT",
    roles=frozenset({"employee", "it_staff"}),
    knowledge_base_ids=frozenset({1}),
    dataset_ids=frozenset(),
)


class FakeMemory:
    async def retrieve_context(
        self,
        query: str,
        access: AccessContext,
    ) -> str:
        del query, access
        return (
            "以下是用户历史上下文，仅供理解用户偏好，"
            "不得作为制度或数据事实依据。\n"
            "- 用户偏好直接给排查步骤。"
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
    def __init__(self) -> None:
        self.system_prompts: list[str] = []

    async def generate(
        self,
        request,
        sensitivity: Sensitivity,
    ) -> GatewayResponse:
        del sensitivity
        self.system_prompts.append(request.system_prompt)
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
    ):
        del question, access
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
async def test_agent_prompt_includes_long_term_memory_as_history_only() -> None:
    gateway = FakeGateway()
    orchestrator = AgentOrchestrator(
        router=RuleRouter(),
        gateway=gateway,
        retrieval=FakeRetrieval(),
        data_service=FakeDataService(),
        prompts=FakePromptResolver(),
        memory=FakeMemory(),
    )

    await orchestrator.run(
        "vpn没有连接怎么办？",
        ACCESS,
    )

    prompt = gateway.system_prompts[0]
    assert "以下是用户历史上下文" in prompt
    assert "不得作为制度或数据事实依据" in prompt
    assert "VPN 无法连接时先检查网络" in prompt


@pytest.mark.asyncio
async def test_memory_does_not_replace_rag_evidence_gate() -> None:
    class NoEvidenceRetrieval:
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
                    level=EvidenceLevel.INSUFFICIENT,
                    citations=[],
                    notice="当前有权限访问的知识库中没有足够证据回答该问题。",
                ),
            )

    gateway = FakeGateway()
    orchestrator = AgentOrchestrator(
        router=RuleRouter(),
        gateway=gateway,
        retrieval=NoEvidenceRetrieval(),
        data_service=FakeDataService(),
        prompts=FakePromptResolver(),
        memory=FakeMemory(),
    )

    result = await orchestrator.run(
        "vpn没有连接怎么办？",
        ACCESS,
    )

    assert result.refused is True
    assert gateway.system_prompts == []
