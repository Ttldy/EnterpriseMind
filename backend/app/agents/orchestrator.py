from app.agents.contracts import (
    AgentType,
    IntentType,
    OrchestratorResult,
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
from app.knowledge.access import AccessContext
from app.knowledge.retrieval import RetrievalService
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


class AgentOrchestrator:
    def __init__(
        self,
        router: RuleRouter,
        gateway: ModelGateway,
        retrieval: RetrievalService,
        data_service: DataQueryService,
    ) -> None:
        self._router = router
        self._gateway = gateway
        self._retrieval = retrieval
        self._data_service = data_service

    async def run(
        self,
        message: str,
        access: AccessContext,
    ) -> OrchestratorResult:
        route = self._router.route(message)

        if route.agent is AgentType.CLARIFICATION:
            return OrchestratorResult(
                answer=("请补充问题所属领域和具体需求。"),
                agent=route.agent,
                intent=route.intent,
                model="none",
                sensitivity=route.sensitivity,
            )

        if route.agent is AgentType.DATA_ANALYST:
            return await self._run_data_query(
                message,
                access,
            )

        return await self._run_knowledge_query(
            message,
            access,
            route.agent,
            route.intent,
            route.sensitivity,
        )

    async def _run_data_query(
        self,
        message: str,
        access: AccessContext,
    ) -> OrchestratorResult:
        try:
            result = await self._data_service.answer(
                message,
                access,
            )
        except PermissionError:
            return OrchestratorResult(
                answer=("当前账号没有可用于该问题的" "授权数据集。"),
                agent=AgentType.DATA_ANALYST,
                intent=self._router.route(message).intent,
                model="none",
                sensitivity=Sensitivity.SENSITIVE,
                refused=True,
            )
        except (
            SqlGenerationError,
            UnsafeSqlError,
        ):
            return OrchestratorResult(
                answer=("生成的查询没有通过安全校验，" "本次请求未执行。"),
                agent=AgentType.DATA_ANALYST,
                intent=self._router.route(message).intent,
                model="none",
                sensitivity=Sensitivity.SENSITIVE,
                refused=True,
            )
        except SensitiveModelUnavailable:
            return OrchestratorResult(
                answer=("本地模型暂时不可用，" "为避免敏感数据外发，" "本次请求已拒绝。"),
                agent=AgentType.DATA_ANALYST,
                intent=self._router.route(message).intent,
                model="none",
                sensitivity=Sensitivity.SENSITIVE,
                refused=True,
            )

        return OrchestratorResult(
            answer=result.answer,
            agent=AgentType.DATA_ANALYST,
            intent=self._router.route(message).intent,
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
        citations = await self._retrieval.search(
            message,
            access,
        )
        if not citations:
            return OrchestratorResult(
                answer=("当前有权限访问的知识库中" "没有足够证据回答该问题。"),
                agent=agent,
                intent=intent,
                model="none",
                sensitivity=route_sensitivity,
                refused=True,
            )

        question_decision = classify_question(message)
        final_sensitivity = highest_sensitivity(
            route_sensitivity,
            question_decision.level,
            *(citation.sensitivity for citation in citations),
        )

        context = self._format_citations(citations)
        system_prompt = (
            f"{PROMPTS[agent]}\n\n"
            "必须只根据以下企业知识片段回答。"
            "证据不足时明确说明无法确认。\n\n"
            f"{context}"
        )

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
                answer=("本地模型暂时不可用，" "为避免受保护内容外发，" "本次请求已拒绝。"),
                agent=agent,
                intent=intent,
                model="none",
                sensitivity=final_sensitivity,
                refused=True,
            )

        return OrchestratorResult(
            answer=response.text,
            agent=agent,
            intent=intent,
            model=response.model,
            sensitivity=final_sensitivity,
            provider=response.provider,
            route_reason=response.route_reason,
            external_sent=response.external_sent,
            citations=tuple(citations),
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
