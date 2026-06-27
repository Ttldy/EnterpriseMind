from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    category: str
    prompt_key: str
    question: str
    username: str | None = None
    expected_agent: str | None = None
    expected_keywords: tuple[str, ...] = ()
    expected_citation: str | None = None
    should_refuse: bool | None = None
    expected_provider: str | None = None
    expected_external_sent: bool | None = None
    sql_must_be_rejected: bool | None = None
    judge_enabled: bool | None = None
    judge_dimensions: tuple[str, ...] = ()
    minimum_judge_score: float | None = None
    notes: str | None = None
    sensitivity: str | None = None


@dataclass(frozen=True)
class CaseOutput:
    answer: str
    agent: str
    provider: str
    refused: bool
    citations: tuple[str, ...] = ()
    intent: str | None = None
    sql_rejected: bool | None = None
    model: str | None = None
    sensitivity: str | None = None
    external_sent: bool | None = None
    sql: str | None = None
    row_count: int | None = None
    metadata: dict[str, object] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class SafetyReport:
    pass_rate: float
    release_allowed: bool


@dataclass(frozen=True)
class Comparison:
    release_allowed: bool
    regressions: tuple[str, ...]


class CaseExecutor(Protocol):
    async def execute(
        self,
        case: EvaluationCase,
        prompt_content: str,
    ) -> CaseOutput:
        ...
