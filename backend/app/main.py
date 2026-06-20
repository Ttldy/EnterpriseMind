from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis

from app.agents.orchestrator import AgentOrchestrator
from app.agents.router import RuleRouter
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.auth.api import router as auth_router
from app.conversations.api import (
    router as conversations_router,
)
from app.conversations.cache import (
    RedisRecentMessageCache,
)
from app.knowledge.api import router as knowledge_router
from app.knowledge.embedding import (
    HashEmbeddingProvider,
)
from app.knowledge.retrieval import RetrievalService
from app.knowledge.vector_store import QdrantVectorStore
from app.model_gateway.contracts import ModelProvider
from app.model_gateway.demo import DemoProvider
from app.shared.config import get_settings
from app.shared.trace import TraceIdMiddleware


def create_app(
    provider: ModelProvider | None = None,
) -> FastAPI:
    settings = get_settings()
    qdrant_client = AsyncQdrantClient(url=settings.qdrant_url)
    embedding = HashEmbeddingProvider(dimensions=settings.embedding_dimensions)
    vector_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=settings.qdrant_collection,
        embedding=embedding,
    )
    retrieval = RetrievalService(
        store=vector_store,
        minimum_score=settings.retrieval_minimum_score,
    )
    redis = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )

    @asynccontextmanager
    async def lifespan(
        app: FastAPI,
    ) -> AsyncIterator[None]:
        await vector_store.ensure_collection()
        settings.upload_directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        yield
        await qdrant_client.close()
        await redis.aclose()

    app = FastAPI(
        title=settings.app_name,
        version="0.2.0",
        description="企业内部知识助手",
        lifespan=lifespan,
    )

    selected_provider = provider or DemoProvider()
    app.state.vector_store = vector_store
    app.state.message_cache = RedisRecentMessageCache(redis)
    app.state.orchestrator = AgentOrchestrator(
        router=RuleRouter(),
        provider=selected_provider,
        retrieval=retrieval,
    )

    app.add_middleware(TraceIdMiddleware)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(
        knowledge_router,
        prefix="/api/v1",
    )
    app.include_router(
        conversations_router,
        prefix="/api/v1",
    )
    return app


app = create_app()
