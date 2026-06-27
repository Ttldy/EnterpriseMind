import pytest

from app.agents.contracts import (
    AgentType,
    IntentType,
    RouteResult,
    Sensitivity,
)
from app.agents.orchestrator import (
    AgentOrchestrator,
)
from app.agents.router import RuleRouter
from app.knowledge.access import AccessContext
from app.knowledge.evidence_gate import (
    EvidenceDecision,
    EvidenceLevel,
)
from app.knowledge.retrieval import EnhancedRetrievalResult
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


def citation(
    sensitivity: str = "internal",
) -> Citation:
    return Citation(
        document_id=1,
        filename="vpn.md",
        page=1,
        text="VPN 无法连接时先检查网络，再确认账号状态。",
        score=0.9,
        sensitivity=sensitivity,
    )


class FakeRetrieval:
    def __init__(
        self,
        decision: EvidenceDecision,
    ) -> None:
        self.decision = decision

    async def retrieve(
        self,
        query: str,
        access: AccessContext,
        limit: int = 5,
    ) -> EnhancedRetrievalResult:
        del query, access, limit
        return EnhancedRetrievalResult(
            queries=("vpn没有连接怎么办？", "VPN 无法连接怎么办？"),
            candidates=(),
            decision=self.decision,
        )


class FakeGateway:
    def __init__(self) -> None:
        self.sensitivities: list[Sensitivity] = []
        self.messages: list[str] = []

    async def generate(
        self,
        request,
        sensitivity: Sensitivity,
    ) -> GatewayResponse:
        self.sensitivities.append(sensitivity)
        self.messages.append(request.system_prompt)
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


class AsyncItRouter:
    async def route(
        self,
        message: str,
    ) -> RouteResult:
        del message
        return RouteResult(
            agent=AgentType.IT,
            intent=IntentType.KNOWLEDGE_QUERY,
            requires_sql=False,
            sensitivity=Sensitivity.INTERNAL,
            confidence=0.88,
        )


def orchestrator(
    retrieval: FakeRetrieval,
    gateway: FakeGateway,
) -> AgentOrchestrator:
    return AgentOrchestrator(
        router=RuleRouter(),
        gateway=gateway,
        retrieval=retrieval,
        data_service=FakeDataService(),
        prompts=FakePromptResolver(),
    )


@pytest.mark.asyncio
async def test_internal_evidence_uses_local() -> None:
    gateway = FakeGateway()
    app = orchestrator(
        FakeRetrieval(
            EvidenceDecision(
                level=EvidenceLevel.FULL,
                citations=[citation()],
            )
        ),
        gateway,
    )

    result = await app.run(
        "vpn没有连接怎么办？",
        ACCESS,
    )

    assert result.agent is AgentType.IT
    assert result.provider == "ollama"
    assert result.external_sent is False
    assert gateway.sensitivities == [Sensitivity.INTERNAL]


@pytest.mark.asyncio
async def test_partial_evidence_adds_boundary_notice() -> None:
    gateway = FakeGateway()
    app = orchestrator(
        FakeRetrieval(
            EvidenceDecision(
                level=EvidenceLevel.PARTIAL,
                citations=[citation()],
                notice="证据有限，以下回答只基于当前可访问知识库中的相关片段。",
            )
        ),
        gateway,
    )

    result = await app.run(
        "vpn没有连接怎么办？",
        ACCESS,
    )

    assert result.answer.startswith("证据有限")
    assert result.refused is False
    assert gateway.sensitivities == [Sensitivity.INTERNAL]


@pytest.mark.asyncio
async def test_no_evidence_refuses_without_calling_model() -> None:
    gateway = FakeGateway()
    app = orchestrator(
        FakeRetrieval(
            EvidenceDecision(
                level=EvidenceLevel.INSUFFICIENT,
                citations=[],
                notice="当前有权限访问的知识库中没有足够证据回答该问题。",
            )
        ),
        gateway,
    )

    result = await app.run(
        "vpn没有连接怎么办？",
        ACCESS,
    )

    assert result.refused is True
    assert result.model == "none"
    assert gateway.sensitivities == []


@pytest.mark.asyncio
async def test_unauthorized_data_query_refuses() -> None:
    app = orchestrator(
        FakeRetrieval(
            EvidenceDecision(
                level=EvidenceLevel.INSUFFICIENT,
                citations=[],
            )
        ),
        FakeGateway(),
    )

    result = await app.run(
        "统计各部门报销金额",
        ACCESS,
    )

    assert result.agent is AgentType.DATA_ANALYST
    assert result.refused is True
    assert result.external_sent is False
    assert result.sql is None


@pytest.mark.asyncio
async def test_orchestrator_accepts_async_intent_router() -> None:
    gateway = FakeGateway()
    app = AgentOrchestrator(
        router=AsyncItRouter(),
        gateway=gateway,
        retrieval=FakeRetrieval(
            EvidenceDecision(
                level=EvidenceLevel.FULL,
                citations=[citation()],
            )
        ),
        data_service=FakeDataService(),
        prompts=FakePromptResolver(),
    )

    result = await app.run(
        "电脑连不上公司内网怎么办",
        ACCESS,
    )

    assert result.agent is AgentType.IT
    assert gateway.sensitivities == [Sensitivity.INTERNAL]
