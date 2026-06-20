from dataclasses import dataclass
from enum import StrEnum

from app.knowledge.schemas import Citation


class AgentType(StrEnum):
    HR = "hr"
    IT = "it"
    FINANCE = "finance"
    DATA_ANALYST = "data_analyst"
    CLARIFICATION = "clarification"


class IntentType(StrEnum):
    KNOWLEDGE_QUERY = "knowledge_query"
    DATA_QUERY = "data_query"
    UNKNOWN = "unknown"


class Sensitivity(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"


@dataclass(frozen=True)
class RouteResult:
    agent: AgentType
    intent: IntentType
    requires_sql: bool
    sensitivity: Sensitivity
    confidence: float


@dataclass(frozen=True)
class OrchestratorResult:
    answer: str
    agent: AgentType
    intent: IntentType
    model: str
    sensitivity: Sensitivity
    citations: tuple[Citation, ...] = ()
    refused: bool = False
