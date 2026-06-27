from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Protocol

from app.agents.contracts import (
    AgentType,
    IntentType,
    RouteResult,
    Sensitivity,
)
from app.agents.router import RuleRouter
from app.knowledge.embedding import EmbeddingProvider
from app.model_gateway.contracts import (
    GatewayResponse,
    ModelRequest,
)
from app.model_gateway.gateway import (
    ModelGateway,
    SensitiveModelUnavailable,
)
from app.model_gateway.sensitivity import (
    classify_question,
    highest_sensitivity,
)


class IntentModelGateway(Protocol):
    async def generate(
        self,
        request: ModelRequest,
        sensitivity: Sensitivity,
    ) -> GatewayResponse: ...


@dataclass(frozen=True)
class StrategyScore:
    agent: AgentType
    intent: IntentType
    requires_sql: bool
    sensitivity: Sensitivity
    confidence: float


class EnterpriseIntentRecognizer:
    def __init__(
        self,
        embedding: EmbeddingProvider | None = None,
        gateway: IntentModelGateway | ModelGateway | None = None,
        pattern_router: RuleRouter | None = None,
        minimum_confidence: float = 0.45,
    ) -> None:
        self._embedding = embedding
        self._gateway = gateway
        self._pattern_router = pattern_router or RuleRouter()
        self._minimum_confidence = minimum_confidence

    async def route(
        self,
        message: str,
    ) -> RouteResult:
        pattern = self._pattern_score(message)
        if pattern.confidence >= 0.85:
            return self._to_result(pattern)

        embedding = await self._embedding_score(message)
        llm = await self._llm_score(message)

        candidates = [
            score
            for score in (pattern, embedding, llm)
            if score is not None
        ]
        best = max(
            candidates,
            key=lambda item: item.confidence,
        )
        if best.confidence < self._minimum_confidence:
            return RouteResult(
                agent=AgentType.CLARIFICATION,
                intent=IntentType.UNKNOWN,
                requires_sql=False,
                sensitivity=classify_question(message).level,
                confidence=best.confidence,
            )
        return self._to_result(best)

    def _pattern_score(
        self,
        message: str,
    ) -> StrategyScore:
        normalized = message.strip().lower()
        unsafe_sql_words = (
            "delete",
            "update",
            "insert",
            "drop",
            "truncate",
            "alter",
            "执行",
            "删除",
            "修改",
        )
        if any(word in normalized for word in unsafe_sql_words) and any(
            word in normalized for word in ("sql", "from", "表", "数据", "reimbursements")
        ):
            return StrategyScore(
                agent=AgentType.DATA_ANALYST,
                intent=IntentType.DATA_QUERY,
                requires_sql=True,
                sensitivity=Sensitivity.SENSITIVE,
                confidence=0.94,
            )

        if "模拟" in normalized:
            if "it" in normalized or "知识检索" in normalized:
                return StrategyScore(
                    agent=AgentType.IT,
                    intent=IntentType.KNOWLEDGE_QUERY,
                    requires_sql=False,
                    sensitivity=classify_question(message).level,
                    confidence=0.88,
                )
            if "财务" in normalized:
                return StrategyScore(
                    agent=AgentType.FINANCE,
                    intent=IntentType.KNOWLEDGE_QUERY,
                    requires_sql=False,
                    sensitivity=classify_question(message).level,
                    confidence=0.88,
                )

        result = self._pattern_router.route(message)
        return StrategyScore(
            agent=result.agent,
            intent=result.intent,
            requires_sql=result.requires_sql,
            sensitivity=result.sensitivity,
            confidence=result.confidence,
        )

    async def _embedding_score(
        self,
        message: str,
    ) -> StrategyScore | None:
        if self._embedding is None:
            return None
        prototypes = {
            AgentType.IT: "电脑 内网 VPN 网络 登录 密码 设备 工单",
            AgentType.FINANCE: "报销 发票 差旅 付款 预算 供应商",
            AgentType.HR: "考勤 请假 年假 入职 离职 福利",
        }
        try:
            query_vector = await self._embedding.embed(message)
            scored: list[tuple[AgentType, float]] = []
            for agent, text in prototypes.items():
                proto_vector = await self._embedding.embed(text)
                scored.append(
                    (
                        agent,
                        self._cosine(
                            query_vector,
                            proto_vector,
                        ),
                    )
                )
        except Exception:
            return None

        agent, similarity = max(
            scored,
            key=lambda item: item[1],
        )
        if similarity <= 0:
            return None
        return StrategyScore(
            agent=agent,
            intent=IntentType.KNOWLEDGE_QUERY,
            requires_sql=False,
            sensitivity=classify_question(message).level,
            confidence=min(
                0.78,
                0.45 + similarity * 0.33,
            ),
        )

    async def _llm_score(
        self,
        message: str,
    ) -> StrategyScore | None:
        if self._gateway is None:
            return None
        sensitivity = classify_question(message).level
        model_sensitivity = (
            Sensitivity.PUBLIC
            if sensitivity is Sensitivity.PUBLIC
            else Sensitivity.SENSITIVE
        )
        try:
            response = await self._gateway.generate(
                ModelRequest(
                    system_prompt=(
                        "你是企业知识助手的意图识别器。"
                        "只返回 JSON，不要输出 Markdown。"
                        "字段：agent、intent、requires_sql、sensitivity、confidence。"
                        "agent 只能是 hr、it、finance、data_analyst、clarification。"
                        "intent 只能是 knowledge_query、data_query、unknown。"
                    ),
                    user_message=message,
                ),
                model_sensitivity,
            )
            payload = json.loads(response.text)
        except (
            SensitiveModelUnavailable,
            Exception,
        ):
            return None

        try:
            agent = AgentType(str(payload.get("agent")))
            intent = IntentType(str(payload.get("intent")))
            raw_sensitivity = Sensitivity(str(payload.get("sensitivity")))
        except ValueError:
            return None
        confidence = self._bounded_float(
            payload.get("confidence"),
            default=0.55,
        )
        return StrategyScore(
            agent=agent,
            intent=intent,
            requires_sql=bool(payload.get("requires_sql")),
            sensitivity=highest_sensitivity(
                sensitivity,
                raw_sensitivity,
            ),
            confidence=min(
                0.90,
                max(0.0, confidence),
            ),
        )

    @staticmethod
    def _to_result(
        score: StrategyScore,
    ) -> RouteResult:
        return RouteResult(
            agent=score.agent,
            intent=score.intent,
            requires_sql=score.requires_sql,
            sensitivity=score.sensitivity,
            confidence=score.confidence,
        )

    @staticmethod
    def _cosine(
        left: list[float],
        right: list[float],
    ) -> float:
        if len(left) != len(right):
            return 0.0
        dot = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)

    @staticmethod
    def _bounded_float(
        value: object,
        default: float,
    ) -> float:
        if isinstance(value, int | float | str):
            try:
                parsed = float(value)
            except ValueError:
                return default
            return min(1.0, max(0.0, parsed))
        return default
