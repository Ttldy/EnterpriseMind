import pytest
from sqlalchemy import select

from app.agents.contracts import AgentType, IntentType, OrchestratorResult, Sensitivity
from app.auth.models import User
from app.evaluation.contracts import EvaluationCase
from app.evaluation.orchestrator_executor import OrchestratorCaseExecutor
from app.knowledge.schemas import Citation


class FakeOrchestrator:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, str, frozenset[str]]] = []

    async def run(
        self,
        message,
        access,
    ) -> OrchestratorResult:
        self.calls.append(
            (
                message,
                access.user_id,
                access.department,
                access.roles,
            )
        )
        return OrchestratorResult(
            answer="VPN troubleshooting answer",
            agent=AgentType.IT,
            intent=IntentType.KNOWLEDGE_QUERY,
            model="qwen2.5:3b",
            sensitivity=Sensitivity.INTERNAL,
            provider="ollama",
            external_sent=False,
            citations=(
                Citation(
                    document_id=1,
                    filename="it-handbook.pdf",
                    page=1,
                    text="VPN troubleshooting",
                    score=0.9,
                    sensitivity="internal",
                ),
            ),
            refused=False,
        )


@pytest.mark.asyncio
async def test_orchestrator_executor_builds_access_context_from_username(
    seeded_session,
) -> None:
    async with seeded_session() as session:
        fake = FakeOrchestrator()
        executor = OrchestratorCaseExecutor(
            session=session,
            orchestrator_factory=lambda: fake,
        )
        case = EvaluationCase(
            case_id="it-e2e",
            category="quality",
            prompt_key="it_agent",
            question="VPN cannot connect",
            username="it01",
        )

        output = await executor.execute(case, "candidate prompt")
        user = await session.scalar(
            select(User).where(User.username == "it01")
        )

    assert user is not None
    assert fake.calls == [
        (
            "VPN cannot connect",
            user.id,
            "IT",
            frozenset({"employee", "it_staff"}),
        )
    ]
    assert output.agent == "it"
    assert output.model == "qwen2.5:3b"
    assert output.sensitivity == "internal"
    assert output.citations == ("it-handbook.pdf",)
    assert output.external_sent is False


@pytest.mark.asyncio
async def test_orchestrator_executor_uses_default_username_for_prompt_key(
    seeded_session,
) -> None:
    async with seeded_session() as session:
        fake = FakeOrchestrator()
        executor = OrchestratorCaseExecutor(
            session=session,
            orchestrator_factory=lambda: fake,
            default_usernames={"it_agent": "it01"},
        )
        case = EvaluationCase(
            case_id="it-default-user",
            category="quality",
            prompt_key="it_agent",
            question="VPN cannot connect",
        )

        await executor.execute(case, "candidate prompt")

    assert fake.calls[0][2] == "IT"
