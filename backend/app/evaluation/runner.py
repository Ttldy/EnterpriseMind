import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluation.contracts import (
    CaseExecutor,
    CaseOutput,
    Comparison,
    EvaluationCase,
)
from app.evaluation.judge import (
    JudgeResult,
    LLMJudgeScorer,
)
from app.evaluation.models import (
    EvaluationRun,
    PromptVersion,
)
from app.evaluation.safety import (
    SafetyEvaluator,
    evaluate_safety_case,
)
from app.evaluation.scorers import (
    average_metrics,
    score_case,
)


def compare_metrics(
    baseline: dict[str, float],
    candidate: dict[str, float],
    maximum_drop: float = 0.03,
) -> Comparison:
    regressions = tuple(
        name
        for name, value in baseline.items()
        if candidate.get(name, 0.0)
        < value - maximum_drop
    )
    return Comparison(
        not regressions,
        regressions,
    )


def load_cases(
    directory: Path,
) -> tuple[list[EvaluationCase], str]:
    rows: list[dict[str, object]] = []
    raw: list[bytes] = []
    for filename in (
        "safety.jsonl",
        "quality.jsonl",
    ):
        content = (
            directory / filename
        ).read_bytes()
        raw.append(content)
        for line in content.decode(
            "utf-8"
        ).splitlines():
            if line.strip():
                rows.append(json.loads(line))

    digest = hashlib.sha256(
        b"\n".join(raw)
    ).hexdigest()
    cases = [
        EvaluationCase(
            case_id=str(row["case_id"]),
            category=str(row["category"]),
            prompt_key=str(row["prompt_key"]),
            question=str(row["question"]),
            username=(
                str(row["username"])
                if row.get("username")
                else None
            ),
            expected_agent=(
                str(row["expected_agent"])
                if row.get("expected_agent")
                else None
            ),
            expected_keywords=tuple(
                str(item)
                for item in cast(
                    list[object],
                    row.get(
                        "expected_keywords",
                        [],
                    ),
                )
            ),
            expected_citation=(
                str(row["expected_citation"])
                if row.get("expected_citation")
                else None
            ),
            should_refuse=(
                bool(row["should_refuse"])
                if "should_refuse" in row
                else None
            ),
            expected_provider=(
                str(row["expected_provider"])
                if row.get("expected_provider")
                else None
            ),
            expected_external_sent=(
                bool(row["expected_external_sent"])
                if "expected_external_sent" in row
                else None
            ),
            sql_must_be_rejected=(
                bool(row["sql_must_be_rejected"])
                if "sql_must_be_rejected" in row
                else None
            ),
            judge_enabled=(
                bool(row["judge_enabled"])
                if "judge_enabled" in row
                else None
            ),
            judge_dimensions=tuple(
                str(item)
                for item in cast(
                    list[object],
                    row.get(
                        "judge_dimensions",
                        [],
                    ),
                )
            ),
            minimum_judge_score=(
                _optional_float(
                    row.get("minimum_judge_score")
                )
                if "minimum_judge_score" in row
                else None
            ),
            notes=(
                str(row["notes"])
                if row.get("notes")
                else None
            ),
            sensitivity=(
                str(row["sensitivity"])
                if row.get("sensitivity")
                else None
            ),
        )
        for row in rows
    ]
    return cases, digest


def _optional_float(
    value: object,
) -> float:
    if isinstance(value, int | float | str):
        return float(value)
    raise TypeError("Expected a numeric value")


class EvaluationRunner:
    def __init__(
        self,
        session: AsyncSession,
        executor: CaseExecutor,
        case_directory: Path,
        model_name: str,
        maximum_drop: float = 0.03,
        judge: LLMJudgeScorer | None = None,
        judge_enabled: bool = True,
        judge_minimum_score: float = 0.75,
        judge_fail_closed: bool = True,
    ) -> None:
        self._session = session
        self._executor = executor
        self._case_directory = case_directory
        self._model_name = model_name
        self._maximum_drop = maximum_drop
        self._judge = judge
        self._judge_enabled = judge_enabled
        self._judge_minimum_score = judge_minimum_score
        self._judge_fail_closed = judge_fail_closed

    async def run(
        self,
        prompt: PromptVersion,
    ) -> EvaluationRun:
        cases, dataset_hash = load_cases(
            self._case_directory
        )
        selected = [
            case
            for case in cases
            if case.prompt_key
            == prompt.prompt_key
        ]
        run = EvaluationRun(
            prompt_version_id=prompt.id,
            status="RUNNING",
            model_name=self._model_name,
            dataset_sha256=dataset_hash,
            metrics={},
            regressions=[],
            case_results=[],
        )
        self._session.add(run)
        await self._session.commit()
        await self._session.refresh(run)

        started = time.perf_counter()
        safety_values: list[bool] = []
        deterministic_values: list[
            dict[str, float]
        ] = []
        judge_values: list[dict[str, float]] = []
        details: list[dict[str, object]] = []

        try:
            for case in selected:
                output = await self._executor.execute(
                    case,
                    prompt.content,
                )
                metrics = score_case(
                    case,
                    output,
                )
                if case.category == "safety":
                    passed = evaluate_safety_case(
                        case,
                        output,
                    )
                    safety_values.append(passed)
                    judge_result = self._skipped_judge()
                else:
                    deterministic_values.append(metrics)
                    judge_result = await self._score_with_judge(
                        case,
                        output,
                    )
                    judge_metrics = self._judge_metrics(
                        judge_result
                    )
                    if judge_metrics:
                        judge_values.append(judge_metrics)
                    passed = self._case_passed(
                        metrics,
                        judge_result,
                        case.minimum_judge_score,
                    )
                details.append(
                    {
                        "case_id": case.case_id,
                        "category": case.category,
                        "passed": passed,
                        "metrics": metrics,
                        "judge_metrics": self._judge_metrics(
                            judge_result
                        ),
                        "reasons": judge_result.reasons,
                        "improvement_suggestions": (
                            judge_result.improvement_suggestions
                        ),
                        "judge_error": judge_result.error,
                        "output": {
                            "agent": output.agent,
                            "provider": output.provider,
                            "model": output.model,
                            "sensitivity": output.sensitivity,
                            "refused": output.refused,
                            "external_sent": output.external_sent,
                            "sql": output.sql,
                            "row_count": output.row_count,
                        },
                    }
                )

            safety = SafetyEvaluator.summarize(
                safety_values
            )
            metrics = average_metrics(
                deterministic_values
            ) | average_metrics(judge_values)
            baseline = await self._baseline_metrics(
                prompt
            )
            comparison = compare_metrics(
                baseline,
                metrics,
                self._maximum_drop,
            )
            run.status = "COMPLETED"
            run.safety_pass_rate = (
                safety.pass_rate
            )
            run.safety_passed = (
                safety.release_allowed
            )
            run.metrics = metrics
            run.regressions = list(
                comparison.regressions
            )
            run.case_results = details
            run.release_allowed = (
                safety.release_allowed
                and comparison.release_allowed
                and self._judge_gate(judge_values)
            )
        except Exception as exc:
            run.status = "FAILED"
            run.error_message = str(exc)[:1000]
            run.duration_ms = int(
                (
                    time.perf_counter()
                    - started
                )
                * 1000
            )
            run.completed_at = datetime.now(UTC)
            await self._session.commit()
            raise

        run.duration_ms = int(
            (
                time.perf_counter()
                - started
            )
            * 1000
        )
        run.completed_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(run)
        return run

    async def _score_with_judge(
        self,
        case: EvaluationCase,
        output: CaseOutput,
    ) -> JudgeResult:
        if (
            not self._judge_enabled
            or self._judge is None
            or case.judge_enabled is False
        ):
            return self._skipped_judge()
        return await self._judge.score(
            case,
            output,
        )

    @staticmethod
    def _skipped_judge() -> JudgeResult:
        return JudgeResult(
            enabled=False,
            available=False,
            scores={},
            overall_score=0.0,
            reasons=[],
            improvement_suggestions=[],
        )

    @staticmethod
    def _judge_metrics(
        result: JudgeResult,
    ) -> dict[str, float]:
        if not result.enabled:
            return {}
        return {
            "judge_relevance": result.scores.get(
                "relevance",
                0.0,
            ),
            "judge_accuracy": result.scores.get(
                "accuracy",
                0.0,
            ),
            "judge_completeness": result.scores.get(
                "completeness",
                0.0,
            ),
            "judge_usefulness": result.scores.get(
                "usefulness",
                0.0,
            ),
            "judge_overall": result.overall_score,
        }

    def _case_passed(
        self,
        metrics: dict[str, float],
        judge_result: JudgeResult,
        minimum_judge_score: float | None,
    ) -> bool:
        deterministic_passed = all(
            value >= 1.0 for value in metrics.values()
        )
        if not judge_result.enabled:
            return deterministic_passed
        if not judge_result.available:
            return (
                deterministic_passed
                and not self._judge_fail_closed
            )
        return deterministic_passed and (
            judge_result.overall_score
            >= (
                minimum_judge_score
                or self._judge_minimum_score
            )
        )

    def _judge_gate(
        self,
        judge_values: list[dict[str, float]],
    ) -> bool:
        if not self._judge_enabled:
            return True
        if not judge_values:
            return not self._judge_fail_closed
        overall = average_metrics(judge_values).get(
            "judge_overall",
            0.0,
        )
        return overall >= self._judge_minimum_score

    async def _baseline_metrics(
        self,
        prompt: PromptVersion,
    ) -> dict[str, float]:
        active = await self._session.scalar(
            select(PromptVersion).where(
                PromptVersion.prompt_key
                == prompt.prompt_key,
                PromptVersion.is_active.is_(True),
            )
        )
        if active is None or active.id == prompt.id:
            return {}
        run = await self._session.scalar(
            select(EvaluationRun)
            .where(
                EvaluationRun.prompt_version_id
                == active.id,
                EvaluationRun.status
                == "COMPLETED",
            )
            .order_by(EvaluationRun.id.desc())
        )
        return run.metrics if run else {}
