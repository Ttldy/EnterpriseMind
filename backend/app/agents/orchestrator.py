from app.agents.contracts import (
    AgentType,
    OrchestratorResult,
)
from app.agents.domain_agents import PROMPTS
from app.agents.router import RuleRouter
from app.model_gateway.contracts import (
    ModelProvider,
    ModelRequest,
)


class AgentOrchestrator:
    def __init__(
        self,
        router: RuleRouter,
        provider: ModelProvider,
    ) -> None:
        self._router = router
        self._provider = provider

    async def run(self, message: str) -> OrchestratorResult:
        route = self._router.route(message)

        if route.agent is AgentType.CLARIFICATION:
            return OrchestratorResult(
                answer="请补充问题所属领域和具体需求。",
                agent=route.agent,
                intent=route.intent,
                model="none",
                sensitivity=route.sensitivity,
            )

        prompt = PROMPTS[route.agent]
        model_response = await self._provider.generate(
            ModelRequest(
                system_prompt=prompt,
                user_message=message,
            )
        )

        return OrchestratorResult(
            answer=model_response.text,
            agent=route.agent,
            intent=route.intent,
            model=model_response.model,
            sensitivity=route.sensitivity,
        )