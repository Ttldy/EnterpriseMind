from __future__ import annotations

from app.agents.contracts import Sensitivity
from app.knowledge.access import AccessContext
from app.knowledge.retrieval import RetrievalService
from app.tools.contracts import ToolContext, ToolSpec


class KnowledgeSearchTool:
    spec = ToolSpec(
        name="knowledge_search",
        description="Permission-aware enterprise knowledge retrieval.",
        input_schema={
            "type": "object",
            "required": ["query", "access"],
            "properties": {
                "query": {"type": "string"},
                "access": {"type": "access_context"},
            },
        },
        timeout_ms=3000,
        cache_enabled=True,
        cache_ttl_seconds=30,
        circuit_breaker_enabled=True,
        fallback_enabled=True,
        required_roles=frozenset({"employee"}),
        sensitivity=Sensitivity.INTERNAL,
    )

    def __init__(
        self,
        retrieval: RetrievalService,
    ) -> None:
        self._retrieval = retrieval

    async def run(
        self,
        payload: dict[str, object],
        context: ToolContext,
    ) -> object:
        query = payload.get("query")
        access = payload.get("access")
        if not isinstance(query, str):
            raise ValueError("query must be a string")
        if not isinstance(access, AccessContext):
            raise ValueError("access must be an AccessContext")
        if access.user_id != context.user_id:
            raise PermissionError("tool context user mismatch")
        return await self._retrieval.retrieve(
            query,
            access,
        )
