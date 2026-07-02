import inspect
from typing import Protocol, cast

from app.agents.composite import (
    CompositePlan,
    CompositeTaskPlanner,
)
from app.agents.contracts import (
    AgentType,
    IntentType,
    OrchestratorResult,
    RouteResult,
    Sensitivity,
)
from app.agents.domain_agents import PROMPTS
from app.agents.router import RuleRouter
from app.database_agent.generator import (
    SqlGenerationError,
)
from app.database_agent.service import (
    DataQueryService,
)
from app.database_agent.validator import (
    UnsafeSqlError,
)
from app.evaluation.resolver import PromptResolver
from app.knowledge.access import AccessContext
from app.knowledge.evidence_gate import EvidenceLevel
from app.knowledge.retrieval import (
    EnhancedRetrievalResult,
    RetrievalService,
)
from app.knowledge.schemas import Citation
from app.model_gateway.contracts import ModelRequest
from app.model_gateway.gateway import (
    ModelGateway,
    SensitiveModelUnavailable,
)
from app.model_gateway.sensitivity import (
    classify_question,
    highest_sensitivity,
)
from app.monitoring.context import current_trace_id
from app.monitoring.contracts import MonitorEvent, MonitorRecorder
from app.monitoring.instrumentation import (
    OperationTimer,
    exception_error_code,
    is_timeout_error,
)
from app.tools.contracts import ToolContext, ToolResult


class LongTermMemory(Protocol):
    async def retrieve_context(
        self,
        query: str,
        access: AccessContext,
    ) -> str: ...


class ToolManagerLike(Protocol):
    async def execute(
        self,
        name: str,
        payload: dict[str, object],
        context: ToolContext,
    ) -> ToolResult: ...


class AgentOrchestrator:
    def __init__(
        self,
        router: RuleRouter,
        gateway: ModelGateway,
        retrieval: RetrievalService,
        data_service: DataQueryService,
        prompts: PromptResolver,
        memory: LongTermMemory | None = None,
        tool_manager: ToolManagerLike | None = None,
        composite_enabled: bool = False,
        composite_planner: CompositeTaskPlanner | None = None,
        monitor: MonitorRecorder | None = None,
    ) -> None:
        self._router = router
        self._gateway = gateway
        self._retrieval = retrieval
        self._data_service = data_service
        self._prompts = prompts
        self._memory = memory
        self._tool_manager = tool_manager
        self._composite_enabled = composite_enabled
        self._composite_planner = composite_planner or CompositeTaskPlanner()
        self._monitor = monitor

    async def run(
        self,
        message: str,
        access: AccessContext,
    ) -> OrchestratorResult:
        timer = OperationTimer(
            self._monitor,
            component="orchestrator",
            operation="run",
        )
        try:
            result = await self._run(message, access)
        except Exception as exc:
            timer.finish(
                success=False,
                error_code=exception_error_code(exc),
                timeout=is_timeout_error(exc),
            )
            raise
        business_outcome = result.metadata.get(
            "business_outcome"
        )
        timer.finish(
            success=True,
            error_code=(
                str(business_outcome)
                if business_outcome
                else None
            ),
            agent=result.agent.value,
            provider=result.provider,
            model=result.model,
            metadata={
                "refused": result.refused,
                "sensitivity": result.sensitivity.value,
                **(
                    {"business_outcome": business_outcome}
                    if business_outcome
                    else {}
                ),
            },
        )
        return result

    async def _run(
        self,
        message: str,
        access: AccessContext,
    ) -> OrchestratorResult:
        if self._composite_enabled:
            plan = self._composite_planner.plan(message)
            if plan is not None:
                return await self._run_composite_query(
                    message,
                    access,
                    plan,
                )

        route = await self._route(message)

        if route.agent is AgentType.CLARIFICATION:
            return OrchestratorResult(
                answer="请补充问题所属领域和具体需求。",
                agent=route.agent,
                intent=route.intent,
                model="none",
                sensitivity=route.sensitivity,
            )

        if route.agent is AgentType.DATA_ANALYST:
            return await self._run_data_query(
                message,
                access,
                route,
            )

        return await self._run_knowledge_query(
            message,
            access,
            route.agent,
            route.intent,
            route.sensitivity,
        )

    async def _run_composite_query(
        self,
        message: str,
        access: AccessContext,
        plan: CompositePlan,
    ) -> OrchestratorResult:
        knowledge = await self._run_knowledge_query(
            message,
            access,
            plan.primary_agent,
            IntentType.KNOWLEDGE_QUERY,
            Sensitivity.INTERNAL,
        )
        data: OrchestratorResult | None = None
        if plan.requires_data_task:
            data = await self._run_data_query(
                message,
                access,
                RouteResult(
                    agent=AgentType.DATA_ANALYST,
                    intent=IntentType.DATA_QUERY,
                    requires_sql=True,
                    sensitivity=Sensitivity.SENSITIVE,
                    confidence=0.85,
                ),
            )

        sections = [
            f"【知识子任务：{plan.knowledge_focus}】\n{knowledge.answer}",
        ]
        if data is not None:
            sections.append(
                f"【数据子任务：{plan.data_focus}】\n{data.answer}"
            )
        partial_success = (
            knowledge.refused
            or (data.refused if data is not None else False)
        )
        all_refused = knowledge.refused and (
            data.refused if data is not None else False
        )
        return OrchestratorResult(
            answer="\n\n".join(sections),
            agent=plan.primary_agent,
            intent=IntentType.KNOWLEDGE_QUERY,
            model=(
                knowledge.model
                if knowledge.model != "none"
                else (data.model if data is not None else "none")
            ),
            sensitivity=(
                Sensitivity.SENSITIVE
                if data is not None
                else knowledge.sensitivity
            ),
            provider=(
                knowledge.provider
                if knowledge.provider != "none"
                else (data.provider if data is not None else "none")
            ),
            route_reason="composite_plan",
            external_sent=(
                knowledge.external_sent
                or (data.external_sent if data is not None else False)
            ),
            citations=knowledge.citations,
            refused=all_refused,
            sql=(data.sql if data is not None else None),
            row_count=(data.row_count if data is not None else None),
            metadata={
                **knowledge.metadata,
                "composite": True,
                "partial_success": partial_success,
                "subtask_count": 2 if data is not None else 1,
                "subtask_success_rate": (
                    sum(
                        not item.refused
                        for item in (knowledge, data)
                        if item is not None
                    )
                    / (2 if data is not None else 1)
                ),
            },
        )

    async def _run_data_query(
        self,
        message: str,
        access: AccessContext,
        route: RouteResult,
    ) -> OrchestratorResult:
        memory_context = await self._retrieve_memory_context(
            message,
            access,
        )
        try:
            result = await self._data_service.answer(
                message,
                access,
                memory_context=memory_context,
            )
        except PermissionError:
            return OrchestratorResult(
                answer="当前账号没有可用于该问题的授权数据集。",
                agent=AgentType.DATA_ANALYST,
                intent=route.intent,
                model="none",
                sensitivity=Sensitivity.SENSITIVE,
                refused=True,
                metadata={
                    "business_outcome": "permission_denied"
                },
            )
        except (
            SqlGenerationError,
            UnsafeSqlError,
        ):
            return OrchestratorResult(
                answer="生成的查询没有通过安全校验，本次请求未执行。",
                agent=AgentType.DATA_ANALYST,
                intent=route.intent,
                model="none",
                sensitivity=Sensitivity.SENSITIVE,
                refused=True,
                metadata={
                    "business_outcome": "unsafe_sql_rejected"
                },
            )
        except SensitiveModelUnavailable:
            return OrchestratorResult(
                answer=(
                    "本地模型暂时不可用，为避免敏感数据外发，"
                    "本次请求已拒绝。"
                ),
                agent=AgentType.DATA_ANALYST,
                intent=route.intent,
                model="none",
                sensitivity=Sensitivity.SENSITIVE,
                refused=True,
                metadata={
                    "business_outcome": (
                        "sensitive_model_unavailable"
                    )
                },
            )

        return OrchestratorResult(
            answer=result.answer,
            agent=AgentType.DATA_ANALYST,
            intent=route.intent,
            model=result.model,
            sensitivity=Sensitivity.SENSITIVE,
            provider=result.provider,
            route_reason=result.route_reason,
            external_sent=result.external_sent,
            sql=result.sql,
            row_count=result.row_count,
        )

    async def _run_knowledge_query(
        self,
        message: str,
        access: AccessContext,
        agent: AgentType,
        intent: IntentType,
        route_sensitivity: Sensitivity,
    ) -> OrchestratorResult:
        memory_context = await self._retrieve_memory_context(
            message,
            access,
        )
        retrieval_result, tool_metadata = await self._retrieve_knowledge(
            message,
            access,
        )
        decision = retrieval_result.decision
        citations = decision.citations
        if decision.level is EvidenceLevel.INSUFFICIENT:
            return OrchestratorResult(
                answer=(
                    decision.notice
                    or "当前有权限访问的知识库中没有足够证据回答该问题。"
                ),
                agent=agent,
                intent=intent,
                model="none",
                sensitivity=route_sensitivity,
                refused=True,
                metadata={
                    **tool_metadata,
                    "business_outcome": (
                        "evidence_insufficient"
                    ),
                },
            )

        question_decision = classify_question(message)
        final_sensitivity = highest_sensitivity(
            route_sensitivity,
            question_decision.level,
            *(citation.sensitivity for citation in citations),
        )

        context = self._format_citations(citations)
        prompt_key = {
            AgentType.HR: "hr_agent",
            AgentType.IT: "it_agent",
            AgentType.FINANCE: "finance_agent",
        }[agent]
        agent_prompt = await self._prompts.resolve(
            prompt_key,
            PROMPTS[agent],
        )
        system_prompt = (
            f"{agent_prompt}\n\n"
            "必须只根据以下企业知识片段回答。"
            "证据不足时明确说明无法确认。\n\n"
            f"{context}"
        )
        if memory_context:
            system_prompt = f"{system_prompt}\n\n{memory_context}"
        if decision.level is EvidenceLevel.PARTIAL and decision.notice:
            system_prompt = f"{system_prompt}\n\n{decision.notice}"

        try:
            response = await self._gateway.generate(
                ModelRequest(
                    system_prompt=system_prompt,
                    user_message=message,
                ),
                final_sensitivity,
            )
        except SensitiveModelUnavailable:
            return OrchestratorResult(
                answer=(
                    "本地模型暂时不可用，为避免受保护内容外发，"
                    "本次请求已拒绝。"
                ),
                agent=agent,
                intent=intent,
                model="none",
                sensitivity=final_sensitivity,
                refused=True,
                metadata={
                    **tool_metadata,
                    "business_outcome": (
                        "sensitive_model_unavailable"
                    ),
                },
            )

        answer = response.text
        if decision.level is EvidenceLevel.PARTIAL and decision.notice:
            answer = f"{decision.notice}\n\n{answer}"

        return OrchestratorResult(
            answer=answer,
            agent=agent,
            intent=intent,
            model=response.model,
            sensitivity=final_sensitivity,
            provider=response.provider,
            route_reason=response.route_reason,
            external_sent=response.external_sent,
            citations=tuple(citations),
            metadata=tool_metadata,
        )

    @staticmethod
    def _format_citations(
        citations: list[Citation],
    ) -> str:
        return "\n\n".join(
            (
                f"[证据 {index}]\n"
                f"文件：{citation.filename}\n"
                f"页码：{citation.page}\n"
                f"内容：{citation.text}"
            )
            for index, citation in enumerate(
                citations,
                start=1,
            )
        )

    async def _retrieve_memory_context(
        self,
        message: str,
        access: AccessContext,
    ) -> str:
        if self._memory is None:
            return ""
        try:
            return await self._memory.retrieve_context(
                message,
                access,
            )
        except Exception:
            return ""

    async def _route(
        self,
        message: str,
    ) -> RouteResult:
        timer = OperationTimer(
            self._monitor,
            component="intent_router",
            operation="route",
        )
        try:
            result = self._router.route(message)
            resolved = (
                cast(RouteResult, await result)
                if inspect.isawaitable(result)
                else result
            )
        except Exception as exc:
            timer.finish(
                success=False,
                error_code=exception_error_code(exc),
                timeout=is_timeout_error(exc),
            )
            raise
        timer.finish(
            success=True,
            agent=resolved.agent.value,
            metadata={
                "sensitivity": resolved.sensitivity.value
            },
        )
        return resolved

    async def _retrieve_knowledge(
        self,
        message: str,
        access: AccessContext,
    ) -> tuple[EnhancedRetrievalResult, dict[str, object]]:
        if self._tool_manager is None:
            result = await self._retrieval.retrieve(
                message,
                access,
            )
            return result, {}

        tool_result = await self._tool_manager.execute(
            "knowledge_search",
            {
                "query": message,
                "access": access,
            },
            ToolContext(
                user_id=access.user_id,
                department=access.department,
                roles=access.roles,
                trace_id=current_trace_id(),
            ),
        )
        metadata = dict(tool_result.metadata)
        if tool_result.success and tool_result.output is not None:
            return (
                cast(EnhancedRetrievalResult, tool_result.output),
                metadata,
            )

        fallback = await self._retrieval.retrieve(
            message,
            access,
        )
        metadata["tool_fallback"] = True
        if self._monitor is not None:
            self._monitor.record(
                MonitorEvent(
                    trace_id=current_trace_id(),
                    component="tool_manager",
                    operation="knowledge_search_fallback",
                    success=True,
                    latency_ms=tool_result.latency_ms,
                    error_code=tool_result.error_code,
                    timeout=(
                        tool_result.error_code == "timeout"
                    ),
                    fallback=True,
                    circuit_open=tool_result.circuit_open,
                    metadata={
                        "tool_name": "knowledge_search"
                    },
                )
            )
        return fallback, metadata
