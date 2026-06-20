from app.agents.contracts import (
    AgentType,
    OrchestratorResult,
    Sensitivity,
)
from app.agents.domain_agents import PROMPTS
from app.agents.router import RuleRouter
from app.knowledge.access import AccessContext
from app.knowledge.retrieval import RetrievalService
from app.knowledge.schemas import Citation
from app.model_gateway.contracts import (
    ModelProvider,
    ModelRequest,
)


class AgentOrchestrator:
    def __init__(
        self,
        router: RuleRouter,
        provider: ModelProvider,
        retrieval: RetrievalService,
    ) -> None:
        self._router = router
        self._provider = provider
        self._retrieval = retrieval

    async def run(
        self,
        message: str,
        access: AccessContext,
    ) -> OrchestratorResult:
        route = self._router.route(message)

        if route.agent is AgentType.CLARIFICATION:
            return OrchestratorResult(
                answer="请补充问题所属领域和具体需求。",
                agent=route.agent,
                intent=route.intent,
                model="none",
                sensitivity=route.sensitivity,
            )

        if route.agent is AgentType.DATA_ANALYST:
            return OrchestratorResult(
                answer=("数据查询能力将在阶段 2 接入。" "当前请求已识别为数据统计问题。"),
                agent=route.agent,
                intent=route.intent,
                model="none",
                sensitivity=Sensitivity.SENSITIVE,
                refused=True,
            )

        citations = await self._retrieval.search(
            message,
            access,
        )
        if not citations:
            return OrchestratorResult(
                answer=("当前有权限访问的知识库中" "没有足够证据回答该问题。"),
                agent=route.agent,
                intent=route.intent,
                model="none",
                sensitivity=route.sensitivity,
                refused=True,
            )

        context = self._format_citations(citations)
        system_prompt = (
            f"{PROMPTS[route.agent]}\n\n"
            "必须只根据以下企业知识片段回答。"
            "证据不足时明确说明无法确认。\n\n"
            f"{context}"
        )
        model_response = await self._provider.generate(
            ModelRequest(
                system_prompt=system_prompt,
                user_message=message,
            )
        )

        sensitivity = self._highest_sensitivity(
            route.sensitivity,
            citations,
        )
        return OrchestratorResult(
            answer=model_response.text,
            agent=route.agent,
            intent=route.intent,
            model=model_response.model,
            sensitivity=sensitivity,
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

    @staticmethod
    def _highest_sensitivity(
        route_sensitivity: Sensitivity,
        citations: list[Citation],
    ) -> Sensitivity:
        order = {
            Sensitivity.PUBLIC: 0,
            Sensitivity.INTERNAL: 1,
            Sensitivity.SENSITIVE: 2,
        }
        result = route_sensitivity
        for citation in citations:
            candidate = Sensitivity(citation.sensitivity)
            if order[candidate] > order[result]:
                result = candidate
        return result
