from app.evaluation.benchmark_compare import compare_reports


def test_compare_reports_calculates_delta_and_relative_change() -> None:
    result = compare_reports(
        baseline={
            "benchmark_name": "EnterpriseMind Agent Benchmark",
            "profile": "baseline",
            "case_count": 10,
            "metrics": {
                "route_accuracy": 0.8,
                "unsafe_sql_block_rate": 1.0,
            },
        },
        enhanced={
            "benchmark_name": "EnterpriseMind Agent Benchmark",
            "profile": "enhanced",
            "case_count": 10,
            "metrics": {
                "route_accuracy": 0.9,
                "unsafe_sql_block_rate": 1.0,
            },
        },
    )

    assert result["baseline_profile"] == "baseline"
    assert result["enhanced_profile"] == "enhanced"
    assert result["metrics"]["route_accuracy"] == {
        "baseline": 0.8,
        "enhanced": 0.9,
        "delta": 0.1,
        "relative_change": 0.125,
    }
    assert result["metrics"]["unsafe_sql_block_rate"]["delta"] == 0.0
    assert any(
        "项目内 benchmark 测试集" in item
        for item in result["interview_summary"]
    )


def test_compare_reports_handles_zero_baseline_without_dividing_by_zero() -> None:
    result = compare_reports(
        baseline={
            "profile": "baseline",
            "case_count": 1,
            "metrics": {"tool_cache_hit_rate": 0.0},
        },
        enhanced={
            "profile": "enhanced",
            "case_count": 1,
            "metrics": {"tool_cache_hit_rate": 0.5},
        },
    )

    assert result["metrics"]["tool_cache_hit_rate"] == {
        "baseline": 0.0,
        "enhanced": 0.5,
        "delta": 0.5,
        "relative_change": None,
    }
    assert any(
        "baseline 为 0" in item
        for item in result["notes"]
    )


def test_compare_reports_warns_when_metric_is_missing() -> None:
    result = compare_reports(
        baseline={
            "profile": "baseline",
            "case_count": 1,
            "metrics": {"route_accuracy": 0.8},
        },
        enhanced={
            "profile": "enhanced",
            "case_count": 1,
            "metrics": {},
        },
    )

    assert result["metrics"]["route_accuracy"]["enhanced"] is None
    assert any(
        "缺少指标 route_accuracy" in item
        for item in result["notes"]
    )


def test_compare_reports_summarizes_tool_resilience_metrics() -> None:
    result = compare_reports(
        baseline={
            "profile": "baseline",
            "case_count": 3,
            "metrics": {
                "tool_timeout_rate": 0.0,
                "tool_fallback_rate": 0.0,
                "tool_circuit_open_count": 0.0,
            },
        },
        enhanced={
            "profile": "enhanced",
            "case_count": 3,
            "metrics": {
                "tool_timeout_rate": 1.0,
                "tool_fallback_rate": 1.0,
                "tool_circuit_open_count": 1.0,
            },
        },
    )

    summary = "\n".join(result["interview_summary"])
    assert "工具超时识别率" in summary
    assert "工具降级触发率" in summary
    assert "工具熔断触发数" in summary
