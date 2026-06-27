from app.evaluation.benchmark_contracts import BenchmarkCase
from app.evaluation.benchmark_metrics import score_benchmark_case
from app.evaluation.contracts import CaseOutput, EvaluationCase


def test_benchmark_metrics_include_tool_runtime_flags() -> None:
    case = BenchmarkCase(
        evaluation=EvaluationCase(
            case_id="tool-timeout",
            category="quality",
            prompt_key="it_agent",
            question="tool timeout",
        ),
        benchmark_module="tools",
        expected_tool_success=False,
        expected_tool_timeout=True,
        expected_tool_fallback=True,
        expected_tool_circuit_open=True,
    )
    output = CaseOutput(
        answer="fallback answer",
        agent="it",
        provider="ollama",
        refused=False,
        metadata={
            "tool_success": False,
            "tool_timeout": True,
            "tool_fallback": True,
            "tool_circuit_open": True,
        },
    )

    metrics = score_benchmark_case(case, output)

    assert metrics["tool_success_rate"] == 1.0
    assert metrics["tool_timeout_rate"] == 1.0
    assert metrics["tool_fallback_rate"] == 1.0
    assert metrics["tool_circuit_open_count"] == 1.0
