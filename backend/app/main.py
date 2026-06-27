from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.intent_recognizer import (
    EnterpriseIntentRecognizer,
)
from app.agents.router import RuleRouter
from app.api.chat import router as chat_router
from app.api.chat_stream import (
    router as chat_stream_router,
)
from app.api.health import router as health_router
from app.auth.admin_api import router as user_admin_router
from app.auth.api import router as auth_router
from app.conversations.api import (
    router as conversations_router,
)
from app.conversations.cache import (
    RedisRecentMessageCache,
)
from app.conversations.memory_service import (
    LongTermMemoryService,
)
from app.conversations.memory_store import (
    QdrantLongTermMemoryStore,
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
from app.evaluation.api import (
    router as evaluation_router,
)
from app.knowledge.api import (
    router as knowledge_router,
)
from app.knowledge.embedding import (
    OllamaEmbeddingProvider,
)
from app.knowledge.evidence_gate import EvidenceGate
from app.knowledge.query_rewriter import QueryRewriter
from app.knowledge.reranker import SensitiveAwareReranker
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
from app.monitoring.service import MonitoringService
from app.shared.config import get_settings
from app.shared.trace import TraceIdMiddleware
from app.tools.builtins import KnowledgeSearchTool
from app.tools.manager import EnterpriseToolManager


def create_app() -> FastAPI:
    settings = get_settings()

    qdrant_client = AsyncQdrantClient(url=settings.qdrant_url)
    embedding = OllamaEmbeddingProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_embedding_model,
        dimensions=settings.embedding_dimensions,
        timeout_seconds=(settings.ollama_embedding_timeout_seconds),
    )
    vector_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=settings.qdrant_collection,
        embedding=embedding,
    )
    memory_store = QdrantLongTermMemoryStore(
        client=qdrant_client,
        collection_name=settings.memory_collection,
        embedding=embedding,
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
    retrieval = RetrievalService(
        store=vector_store,
        minimum_score=(settings.retrieval_minimum_score),
        rewriter=QueryRewriter(gateway),
        reranker=SensitiveAwareReranker(
            gateway,
            maximum_candidates=(settings.retrieval_rerank_candidates),
        ),
        gate=EvidenceGate(
            full_answer_score=(settings.retrieval_full_answer_score),
            partial_answer_score=(settings.retrieval_partial_answer_score),
            minimum_hit_count=(settings.retrieval_minimum_hit_count),
        ),
    )
    long_term_memory = LongTermMemoryService(
        store=memory_store,
        gateway=gateway,
        enabled=settings.memory_enabled,
        trigger_messages=(
            settings.memory_summary_trigger_messages
        ),
        recent_messages=(
            settings.memory_summary_recent_messages
        ),
        max_summary_chars=settings.memory_summary_max_chars,
        top_k=settings.memory_top_k,
        minimum_score=settings.memory_minimum_score,
    )
    tool_manager = None
    if settings.tool_manager_enabled:
        tool_manager = EnterpriseToolManager(
            default_timeout_ms=settings.tool_default_timeout_ms,
            default_cache_ttl_seconds=(
                settings.tool_default_cache_ttl_seconds
            ),
            circuit_failure_threshold=(
                settings.tool_circuit_failure_threshold
            ),
            circuit_recovery_seconds=(
                settings.tool_circuit_recovery_seconds
            ),
        )
        tool_manager.register(
            KnowledgeSearchTool(retrieval)
        )
    monitoring_service = (
        MonitoringService()
        if settings.monitor_enabled
        else None
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
        await memory_store.ensure_collection()
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origin_list,
        allow_credentials=False,
        allow_methods=[
            "GET",
            "POST",
            "PATCH",
            "DELETE",
            "OPTIONS",
        ],
        allow_headers=[
            "Authorization",
            "Content-Type",
        ],
        expose_headers=["X-Trace-ID"],
    )

    app.state.vector_store = vector_store
    app.state.message_cache = RedisRecentMessageCache(redis)
    app.state.long_term_memory = long_term_memory
    app.state.tool_manager = tool_manager
    app.state.composite_agent_enabled = (
        settings.composite_agent_enabled
    )
    app.state.monitoring_service = monitoring_service

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
    app.state.router = (
        EnterpriseIntentRecognizer(
            embedding=embedding,
            gateway=gateway,
            pattern_router=RuleRouter(),
        )
        if settings.intent_router_mode == "hybrid"
        else RuleRouter()
    )

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
    app.include_router(
        user_admin_router,
        prefix="/api/v1",
    )
    app.include_router(
        chat_stream_router,
        prefix="/api/v1",
    )
    app.include_router(
        evaluation_router,
        prefix="/api/v1",
    )
    return app


app = create_app()
