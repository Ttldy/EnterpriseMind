from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.database_agent.executor import (
    ReadOnlyExecutor,
    create_readonly_engine,
)
from app.database_agent.generator import SqlGenerator
from app.database_agent.repository import (
    SqlAlchemyDatasetRepository,
)
from app.database_agent.service import DataQueryService
from app.knowledge.api import (
    router as knowledge_router,
)
from app.knowledge.embedding import (
    HashEmbeddingProvider,
)
from app.knowledge.retrieval import RetrievalService
from app.knowledge.vector_store import (
    QdrantVectorStore,
)
from app.model_gateway.contracts import ModelProvider
from app.model_gateway.demo import DemoProvider
from app.model_gateway.external import (
    ExternalModelProvider,
)
from app.model_gateway.gateway import ModelGateway
from app.model_gateway.ollama import OllamaProvider
from app.shared.config import get_settings
from app.shared.trace import TraceIdMiddleware


def create_app() -> FastAPI:
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
        minimum_score=(settings.retrieval_minimum_score),
    )

    redis = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )

    local_provider = OllamaProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=(settings.ollama_timeout_seconds),
    )
    external_provider: ModelProvider
    if settings.external_model_api_key:
        external_provider = ExternalModelProvider(
            base_url=(settings.external_model_base_url),
            api_key=(settings.external_model_api_key),
            model=settings.external_model_name,
            timeout_seconds=(settings.external_model_timeout_seconds),
        )
    else:
        external_provider = DemoProvider(model="external-demo")

    gateway = ModelGateway(
        local=local_provider,
        external=external_provider,
        allow_external_for_internal=(settings.allow_external_for_internal),
    )

    readonly_engine = create_readonly_engine(settings.readonly_database_url)
    readonly_executor = ReadOnlyExecutor(
        readonly_engine,
        timeout_seconds=(settings.sql_timeout_seconds),
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
        await readonly_engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version="0.3.0",
        description="企业内部知识与数据助手",
        lifespan=lifespan,
    )

    app.state.vector_store = vector_store
    app.state.message_cache = RedisRecentMessageCache(redis)

    def data_service_factory(
        session: AsyncSession,
    ) -> DataQueryService:
        return DataQueryService(
            datasets=(SqlAlchemyDatasetRepository(session)),
            generator=SqlGenerator(gateway),
            executor=readonly_executor,
            gateway=gateway,
            max_rows=settings.sql_max_rows,
        )

    app.state.gateway = gateway
    app.state.retrieval = retrieval
    app.state.data_service_factory = data_service_factory
    app.state.router = RuleRouter()

    app.add_middleware(TraceIdMiddleware)
    app.include_router(
        health_router,
        prefix="/api/v1",
    )
    app.include_router(
        auth_router,
        prefix="/api/v1",
    )
    app.include_router(
        chat_router,
        prefix="/api/v1",
    )
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
