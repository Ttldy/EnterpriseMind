from __future__ import annotations

from app.evaluation.benchmark_contracts import BenchmarkCase
from app.evaluation.contracts import CaseOutput
from app.evaluation.scorers import score_case


def score_benchmark_case(
    case: BenchmarkCase,
    output: CaseOutput,
) -> dict[str, float]:
    metrics = score_case(
        case.evaluation,
        output,
    )
    if case.expected_intent is not None:
        metrics["intent_accuracy"] = float(
            output.intent == case.expected_intent
        )
    if case.expected_sensitivity is not None:
        metrics["sensitivity_accuracy"] = float(
            output.sensitivity == case.expected_sensitivity
        )
    if case.expected_requires_sql is not None:
        actual_requires_sql = (
            output.agent == "data_analyst"
            or bool(output.sql)
            or output.row_count is not None
        )
        metrics["requires_sql_accuracy"] = float(
            actual_requires_sql == case.expected_requires_sql
        )
    if case.expected_tool_success is not None:
        metrics["tool_success_rate"] = float(
            bool(output.metadata.get("tool_success"))
            == case.expected_tool_success
        )
    if case.expected_tool_cache_hit is not None:
        metrics["tool_cache_hit_rate"] = float(
            bool(output.metadata.get("tool_cache_hit"))
            == case.expected_tool_cache_hit
        )
    if case.expected_tool_timeout is not None:
        metrics["tool_timeout_rate"] = float(
            bool(output.metadata.get("tool_timeout"))
            == case.expected_tool_timeout
        )
    if case.expected_tool_fallback is not None:
        metrics["tool_fallback_rate"] = float(
            bool(output.metadata.get("tool_fallback"))
            == case.expected_tool_fallback
        )
    if case.expected_tool_circuit_open is not None:
        metrics["tool_circuit_open_count"] = float(
            bool(output.metadata.get("tool_circuit_open"))
            == case.expected_tool_circuit_open
        )
    if case.expected_permission_block is not None:
        metrics["permission_block_rate"] = float(
            bool(output.metadata.get("permission_block"))
            == case.expected_permission_block
        )
    if case.expected_unsafe_sql_block is not None:
        metrics["unsafe_sql_block_rate"] = float(
            bool(output.sql_rejected)
            == case.expected_unsafe_sql_block
        )
    if case.expected_composite is not None:
        metrics["composite_detection_accuracy"] = float(
            bool(output.metadata.get("composite"))
            == case.expected_composite
        )
    if case.expected_monitor_warning is not None:
        metrics["monitor_warning_detection_accuracy"] = float(
            bool(output.metadata.get("monitor_warning_detected"))
            == case.expected_monitor_warning
        )
    penalty_delta = output.metadata.get("monitor_penalty_delta")
    if isinstance(penalty_delta, int | float):
        metrics["monitor_penalty_delta"] = float(
            penalty_delta
        )
    return metrics
