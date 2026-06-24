from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    category: str
    prompt_key: str
    question: str
    expected_agent: str | None = None
    expected_keywords: tuple[str, ...] = ()
    expected_citation: str | None = None
    should_refuse: bool | None = None
    expected_provider: str | None = None
    sql_must_be_rejected: bool | None = None


@dataclass(frozen=True)
class CaseOutput:
    answer: str
    agent: str
    provider: str
    refused: bool
    citations: tuple[str, ...] = ()
    sql_rejected: bool | None = None


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