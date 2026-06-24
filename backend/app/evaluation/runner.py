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
    Comparison,
    EvaluationCase,
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
            sql_must_be_rejected=(
                bool(row["sql_must_be_rejected"])
                if "sql_must_be_rejected" in row
                else None
            ),
        )
        for row in rows
    ]
    return cases, digest


class EvaluationRunner:
    def __init__(
        self,
        session: AsyncSession,
        executor: CaseExecutor,
        case_directory: Path,
        model_name: str,
        maximum_drop: float = 0.03,
    ) -> None:
        self._session = session
        self._executor = executor
        self._case_directory = case_directory
        self._model_name = model_name
        self._maximum_drop = maximum_drop

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
        quality_values: list[
            dict[str, float]
        ] = []
        details: list[dict[str, object]] = []

        try:
            for case in selected:
                output = await self._executor.execute(
                    case,
                    prompt.content,
                )
                if case.category == "safety":
                    passed = evaluate_safety_case(
                        case,
                        output,
                    )
                    safety_values.append(passed)
                    metrics: dict[str, float] = {}
                else:
                    metrics = score_case(
                        case,
                        output,
                    )
                    quality_values.append(metrics)
                    passed = all(
                        value >= 1.0
                        for value in metrics.values()
                    )
                details.append(
                    {
                        "case_id": case.case_id,
                        "category": case.category,
                        "passed": passed,
                        "metrics": metrics,
                    }
                )

            safety = SafetyEvaluator.summarize(
                safety_values
            )
            metrics = average_metrics(
                quality_values
            )
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
