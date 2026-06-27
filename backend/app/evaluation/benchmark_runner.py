from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from app.evaluation.benchmark_contracts import (
    BenchmarkCase,
    BenchmarkModule,
    BenchmarkProfile,
    JsonDict,
)
from app.evaluation.benchmark_metrics import (
    score_benchmark_case,
)
from app.evaluation.contracts import (
    CaseExecutor,
    EvaluationCase,
)
from app.evaluation.judge import (
    JudgeResult,
    LLMJudgeScorer,
)
from app.evaluation.scorers import average_metrics

BENCHMARK_CASE_FILES = (
    "intent.jsonl",
    "tools.jsonl",
    "composite.jsonl",
    "monitoring.jsonl",
)


def load_benchmark_cases(
    directory: Path,
) -> tuple[list[BenchmarkCase], str]:
    raw_parts: list[bytes] = []
    cases: list[BenchmarkCase] = []
    for filename in BENCHMARK_CASE_FILES:
        path = directory / filename
        if not path.exists():
            continue
        content = path.read_bytes()
        raw_parts.append(content)
        for line in content.decode(
            "utf-8"
        ).splitlines():
            if not line.strip():
                continue
            cases.append(
                _parse_benchmark_case(
                    json.loads(line)
                )
            )
    digest = hashlib.sha256(
        b"\n".join(raw_parts)
    ).hexdigest()
    return cases, digest


class BenchmarkRunner:
    def __init__(
        self,
        executor: CaseExecutor,
        case_directory: Path,
        prompt_content: str,
        judge: LLMJudgeScorer | None = None,
        judge_enabled: bool = False,
    ) -> None:
        self._executor = executor
        self._case_directory = case_directory
        self._prompt_content = prompt_content
        self._judge = judge
        self._judge_enabled = judge_enabled

    async def run(
        self,
        profile: BenchmarkProfile,
    ) -> JsonDict:
        cases, dataset_hash = load_benchmark_cases(
            self._case_directory
        )
        started = time.perf_counter()
        metric_values: list[dict[str, float]] = []
        case_results: list[JsonDict] = []

        for benchmark_case in cases:
            output = await self._executor.execute(
                benchmark_case.evaluation,
                self._prompt_content,
            )
            metrics = score_benchmark_case(
                benchmark_case,
                output,
            )
            judge_result = await self._score_with_judge(
                benchmark_case.evaluation,
                output,
            )
            judge_metrics = self._judge_metrics(
                judge_result
            )
            metrics.update(judge_metrics)
            metric_values.append(metrics)
            case_results.append(
                {
                    "case_id": benchmark_case.evaluation.case_id,
                    "category": benchmark_case.evaluation.category,
                    "benchmark_module": (
                        benchmark_case.benchmark_module
                    ),
                    "metrics": metrics,
                    "output": {
                        "agent": output.agent,
                        "intent": output.intent,
                        "provider": output.provider,
                        "sensitivity": output.sensitivity,
                        "refused": output.refused,
                        "external_sent": output.external_sent,
                        "sql": output.sql,
                        "row_count": output.row_count,
                    },
                    "reasons": judge_result.reasons,
                    "improvement_suggestions": (
                        judge_result.improvement_suggestions
                    ),
                    "judge_error": judge_result.error,
                }
            )

        return {
            "benchmark_name": "EnterpriseMind Agent Benchmark",
            "profile": profile.name,
            "profile_settings": profile.settings,
            "case_count": len(cases),
            "dataset_sha256": dataset_hash,
            "generated_at": datetime.now(UTC).isoformat(),
            "duration_ms": int(
                (time.perf_counter() - started) * 1000
            ),
            "metrics": average_metrics(metric_values),
            "case_results": case_results,
            "notes": [
                "本报告基于项目内 benchmark 测试集生成，用于校招项目能力展示。",
                "baseline/enhanced 通过配置 profile 切换，避免依赖 Git 分支。",
            ],
        }

    async def _score_with_judge(
        self,
        case: EvaluationCase,
        output: object,
    ) -> JudgeResult:
        if (
            not self._judge_enabled
            or self._judge is None
            or case.category == "safety"
            or case.judge_enabled is False
        ):
            return JudgeResult(
                enabled=False,
                available=False,
                scores={},
                overall_score=0.0,
                reasons=[],
                improvement_suggestions=[],
            )
        return await self._judge.score(
            case,
            output,  # type: ignore[arg-type]
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


def _parse_benchmark_case(
    row: JsonDict,
) -> BenchmarkCase:
    module = cast(
        BenchmarkModule,
        str(row.get("benchmark_module", "intent")),
    )
    evaluation = EvaluationCase(
        case_id=str(row["case_id"]),
        category=str(row.get("category", "quality")),
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
                row.get("expected_keywords", []),
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
    return BenchmarkCase(
        evaluation=evaluation,
        benchmark_module=module,
        expected_intent=_optional_str(
            row,
            "expected_intent",
        ),
        expected_requires_sql=_optional_bool(
            row,
            "expected_requires_sql",
        ),
        expected_sensitivity=_optional_str(
            row,
            "expected_sensitivity",
        ),
        expected_tool_success=_optional_bool(
            row,
            "expected_tool_success",
        ),
        expected_tool_cache_hit=_optional_bool(
            row,
            "expected_tool_cache_hit",
        ),
        expected_tool_timeout=_optional_bool(
            row,
            "expected_tool_timeout",
        ),
        expected_tool_fallback=_optional_bool(
            row,
            "expected_tool_fallback",
        ),
        expected_tool_circuit_open=_optional_bool(
            row,
            "expected_tool_circuit_open",
        ),
        expected_permission_block=_optional_bool(
            row,
            "expected_permission_block",
        ),
        expected_unsafe_sql_block=_optional_bool(
            row,
            "expected_unsafe_sql_block",
        ),
        expected_composite=_optional_bool(
            row,
            "expected_composite",
        ),
        expected_monitor_warning=_optional_bool(
            row,
            "expected_monitor_warning",
        ),
        notes=evaluation.notes,
    )


def _optional_str(
    row: JsonDict,
    key: str,
) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    return str(value)


def _optional_bool(
    row: JsonDict,
    key: str,
) -> bool | None:
    if key not in row:
        return None
    return bool(row[key])
