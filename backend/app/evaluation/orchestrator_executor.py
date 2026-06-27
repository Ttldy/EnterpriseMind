from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.contracts import OrchestratorResult
from app.agents.orchestrator import (
    AgentOrchestrator,
    LongTermMemory,
)
from app.agents.router import RuleRouter
from app.auth.models import User
from app.database_agent.service import DataQueryService
from app.evaluation.contracts import CaseOutput, EvaluationCase
from app.evaluation.resolver import PromptResolver
from app.knowledge.access import (
    AccessContext,
    build_access_context,
)
from app.knowledge.retrieval import RetrievalService
from app.model_gateway.gateway import ModelGateway
from app.monitoring.service import MonitoringService
from app.tools.manager import EnterpriseToolManager


class OrchestratorLike(Protocol):
    async def run(
        self,
        message: str,
        access: AccessContext,
    ) -> OrchestratorResult: ...


class StaticCandidatePromptResolver:
    def __init__(
        self,
        prompt_key: str,
        prompt_content: str,
        fallback: PromptResolver,
    ) -> None:
        self._prompt_key = prompt_key
        self._prompt_content = prompt_content
        self._fallback = fallback

    async def resolve(
        self,
        prompt_key: str,
        default: str,
    ) -> str:
        if prompt_key == self._prompt_key:
            return self._prompt_content
        return await self._fallback.resolve(
            prompt_key,
            default,
        )


class OrchestratorCaseExecutor:
    def __init__(
        self,
        session: AsyncSession,
        router: RuleRouter | None = None,
        gateway: ModelGateway | None = None,
        retrieval: RetrievalService | None = None,
        data_service: DataQueryService | None = None,
        prompts: PromptResolver | None = None,
        memory: LongTermMemory | None = None,
        tool_manager: EnterpriseToolManager | None = None,
        composite_enabled: bool = False,
        monitor: MonitoringService | None = None,
        orchestrator_factory: Callable[[], OrchestratorLike]
        | None = None,
        default_usernames: dict[str, str] | None = None,
    ) -> None:
        self._session = session
        self._router = router
        self._gateway = gateway
        self._retrieval = retrieval
        self._data_service = data_service
        self._prompts = prompts
        self._memory = memory
        self._tool_manager = tool_manager
        self._composite_enabled = composite_enabled
        self._monitor = monitor
        self._orchestrator_factory = orchestrator_factory
        self._default_usernames = default_usernames or {
            "hr_agent": "hr01",
            "it_agent": "it01",
            "finance_agent": "finance01",
            "data_analyst_agent": "finance01",
            "admin": "admin",
            "employee": "employee01",
        }

    async def execute(
        self,
        case: EvaluationCase,
        prompt_content: str,
    ) -> CaseOutput:
        user = await self._load_user(
            self._username_for(case)
        )
        access = await build_access_context(
            self._session,
            user,
        )
        orchestrator = self._build_orchestrator(
            case,
            prompt_content,
        )
        result = await orchestrator.run(
            case.question,
            access,
        )
        return self._to_case_output(
            case,
            result,
        )

    def _build_orchestrator(
        self,
        case: EvaluationCase,
        prompt_content: str,
    ) -> OrchestratorLike:
        if self._orchestrator_factory is not None:
            return self._orchestrator_factory()
        if (
            self._router is None
            or self._gateway is None
            or self._retrieval is None
            or self._data_service is None
            or self._prompts is None
        ):
            raise RuntimeError(
                "Orchestrator dependencies are required"
            )
        return AgentOrchestrator(
            router=self._router,
            gateway=self._gateway,
            retrieval=self._retrieval,
            data_service=self._data_service,
            prompts=StaticCandidatePromptResolver(
                case.prompt_key,
                prompt_content,
                self._prompts,
            ),
            memory=self._memory,
            tool_manager=self._tool_manager,
            composite_enabled=self._composite_enabled,
            monitor=self._monitor,
        )

    def _username_for(
        self,
        case: EvaluationCase,
    ) -> str:
        if case.username:
            return case.username
        if case.category == "safety":
            return self._default_usernames.get(
                "employee",
                "employee01",
            )
        return self._default_usernames.get(
            case.prompt_key,
            "employee01",
        )

    async def _load_user(
        self,
        username: str,
    ) -> User:
        user = await self._session.scalar(
            select(User)
            .where(User.username == username)
            .options(
                selectinload(User.department),
                selectinload(User.roles),
            )
        )
        if user is None:
            raise ValueError(
                f"Evaluation user not found: {username}"
            )
        return user

    @staticmethod
    def _to_case_output(
        case: EvaluationCase,
        result: OrchestratorResult,
    ) -> CaseOutput:
        sql_rejected = (
            result.refused
            if case.sql_must_be_rejected is not None
            else None
        )
        return CaseOutput(
            answer=result.answer,
            agent=result.agent.value,
            intent=result.intent.value,
            provider=result.provider,
            refused=result.refused,
            citations=tuple(
                citation.filename
                for citation in result.citations
            ),
            sql_rejected=sql_rejected,
            model=result.model,
            sensitivity=result.sensitivity.value,
            external_sent=result.external_sent,
            sql=result.sql,
            row_count=result.row_count,
            metadata=result.metadata,
        )
