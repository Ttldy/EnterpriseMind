from typing import Protocol

from app.agents.contracts import Sensitivity
from app.conversations.cache import CachedMessage
from app.conversations.memory_schemas import (
    MemoryRecord,
    MemorySearchHit,
)
from app.knowledge.access import AccessContext
from app.model_gateway.contracts import GatewayResponse, ModelRequest


class LongTermMemoryStore(Protocol):
    async def upsert(
        self,
        record: MemoryRecord,
    ) -> None: ...

    async def search_private(
        self,
        query: str,
        user_id: int,
        limit: int,
        minimum_score: float,
    ) -> list[MemorySearchHit]: ...


class SummaryGateway(Protocol):
    async def generate(
        self,
        request: ModelRequest,
        sensitivity: Sensitivity,
    ) -> GatewayResponse: ...


class LongTermMemoryService:
    _preference_words = (
        "以后",
        "下次",
        "我希望",
        "我更喜欢",
        "请直接",
        "不要解释太多",
    )
    _repeated_issue_words = (
        "vpn",
        "报销",
        "发票",
        "请假",
        "密码",
    )

    def __init__(
        self,
        store: LongTermMemoryStore,
        gateway: SummaryGateway,
        enabled: bool,
        trigger_messages: int,
        recent_messages: int,
        max_summary_chars: int,
        top_k: int,
        minimum_score: float,
    ) -> None:
        self._store = store
        self._gateway = gateway
        self._enabled = enabled
        self._trigger_messages = trigger_messages
        self._recent_messages = recent_messages
        self._max_summary_chars = max_summary_chars
        self._top_k = top_k
        self._minimum_score = minimum_score

    async def retrieve_context(
        self,
        query: str,
        access: AccessContext,
    ) -> str:
        if not self._enabled:
            return ""
        try:
            hits = await self._store.search_private(
                query=query,
                user_id=access.user_id,
                limit=self._top_k,
                minimum_score=self._minimum_score,
            )
        except Exception:
            return ""

        if not hits:
            return ""

        lines = [
            "以下是用户历史上下文，仅供理解用户偏好，不得作为制度或数据事实依据。",
            "如果历史上下文与当前知识库证据或数据库结果冲突，必须以当前证据为准。",
        ]
        lines.extend(f"- {hit.text}" for hit in hits)
        return "\n".join(lines)

    async def maybe_store_after_turn(
        self,
        access: AccessContext,
        conversation_id: int,
        message_ids: tuple[int, ...],
        recent_messages: list[CachedMessage],
        sensitivity: Sensitivity,
        sql: str | None,
    ) -> None:
        if not self._enabled or not recent_messages:
            return
        selected_messages = recent_messages[-self._recent_messages :]
        if not self._should_store(selected_messages):
            return

        memory_type = self._memory_type(selected_messages)
        source_text = self._format_messages(selected_messages)
        if sql:
            source_text = (
                f"{source_text}\n\n注意：本轮包含敏感数据查询，"
                "摘要不得记录 SQL 语句、具体结果行或个人明细。"
            )

        try:
            response = await self._gateway.generate(
                ModelRequest(
                    system_prompt=(
                        "你是企业知识助手的长期记忆摘要器。"
                        "只输出一段不超过80字的中文摘要。"
                        "摘要只能记录用户偏好、长期问题或上下文线索，"
                        "不得记录完整原文、SQL、个人敏感明细或未授权知识库片段。"
                    ),
                    user_message=source_text[: self._max_summary_chars],
                ),
                sensitivity,
            )
            summary = response.text.strip()
            if not summary:
                return
            await self._store.upsert(
                MemoryRecord(
                    user_id=access.user_id,
                    department=access.department,
                    roles=tuple(sorted(access.roles)),
                    conversation_id=conversation_id,
                    message_ids=message_ids,
                    memory_type=memory_type,
                    sensitivity=sensitivity.value,
                    text=summary,
                )
            )
        except Exception:
            return

    def _should_store(
        self,
        messages: list[CachedMessage],
    ) -> bool:
        if len(messages) >= self._trigger_messages:
            return True
        text = "\n".join(message.content.lower() for message in messages)
        if any(word in text for word in self._preference_words):
            return True
        return any(
            text.count(word) >= 2
            for word in self._repeated_issue_words
        )

    def _memory_type(
        self,
        messages: list[CachedMessage],
    ) -> str:
        text = "\n".join(message.content.lower() for message in messages)
        if any(word in text for word in self._preference_words):
            return "user_preference"
        if any(
            text.count(word) >= 2
            for word in self._repeated_issue_words
        ):
            return "repeated_issue"
        return "conversation_summary"

    @staticmethod
    def _format_messages(
        messages: list[CachedMessage],
    ) -> str:
        return "\n".join(
            f"{message.role}: {message.content}"
            for message in messages
        )
