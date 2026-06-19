from fastapi import FastAPI

from app.agents.orchestrator import AgentOrchestrator
from app.agents.router import RuleRouter
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.model_gateway.contracts import ModelProvider
from app.model_gateway.demo import DemoProvider
from app.shared.trace import TraceIdMiddleware


def create_app(
    provider: ModelProvider | None = None,
) -> FastAPI:
    app = FastAPI(
        title="EnterpriseMind",
        version="0.1.0",
        description="企业内部知识助手",
    )

    selected_provider = provider or DemoProvider()
    app.state.orchestrator = AgentOrchestrator(
        router=RuleRouter(),
        provider=selected_provider,
    )

    app.add_middleware(TraceIdMiddleware)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    return app


app = create_app()