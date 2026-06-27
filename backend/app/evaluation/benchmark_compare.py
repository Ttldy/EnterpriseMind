from __future__ import annotations

from app.evaluation.benchmark_contracts import JsonDict


def compare_reports(
    baseline: JsonDict,
    enhanced: JsonDict,
) -> JsonDict:
    baseline_metrics = _metrics(baseline)
    enhanced_metrics = _metrics(enhanced)
    names = sorted(
        set(baseline_metrics)
        | set(enhanced_metrics)
    )
    compared: dict[str, JsonDict] = {}
    notes: list[str] = [
        "以上结果来自项目内 benchmark 测试集，用于校招项目能力展示，"
        "不代表真实企业生产指标。"
    ]

    for name in names:
        base = baseline_metrics.get(name)
        new = enhanced_metrics.get(name)
        delta = (
            round(new - base, 6)
            if base is not None and new is not None
            else None
        )
        relative_change: float | None
        if base is None or new is None:
            relative_change = None
            notes.append(f"缺少指标 {name}，无法计算完整对比。")
        elif base == 0:
            relative_change = None
            notes.append(
                f"指标 {name} 的 baseline 为 0，relative_change 记为 null。"
            )
        else:
            relative_change = round(
                (new - base) / base,
                6,
            )
        compared[name] = {
            "baseline": base,
            "enhanced": new,
            "delta": delta,
            "relative_change": relative_change,
        }

    return {
        "benchmark_name": baseline.get(
            "benchmark_name",
            "EnterpriseMind Agent Benchmark",
        ),
        "case_count": enhanced.get(
            "case_count",
            baseline.get("case_count", 0),
        ),
        "baseline_profile": baseline.get(
            "profile",
            "baseline",
        ),
        "enhanced_profile": enhanced.get(
            "profile",
            "enhanced",
        ),
        "metrics": compared,
        "interview_summary": _summary(compared),
        "notes": notes,
    }


def _metrics(report: JsonDict) -> dict[str, float]:
    raw = report.get("metrics", {})
    if not isinstance(raw, dict):
        return {}
    return {
        str(name): float(value)
        for name, value in raw.items()
        if isinstance(value, int | float)
    }


def _summary(metrics: dict[str, JsonDict]) -> list[str]:
    result: list[str] = []
    labels = {
        "route_accuracy": "路由准确率",
        "intent_accuracy": "意图识别准确率",
        "judge_completeness": "回答完整性",
        "tool_success_rate": "工具调用成功率",
        "tool_cache_hit_rate": "工具缓存命中率",
        "tool_timeout_rate": "工具超时识别率",
        "tool_fallback_rate": "工具降级触发率",
        "tool_circuit_open_count": "工具熔断触发数",
        "permission_block_rate": "权限拦截率",
        "composite_detection_accuracy": "复合问题识别准确率",
        "monitor_warning_detection_accuracy": "监控告警识别准确率",
        "unsafe_sql_block_rate": "危险 SQL 拦截率",
        "sql_rejection_accuracy": "SQL 拒绝准确率",
        "external_sent_accuracy": "外发控制准确率",
    }
    for name, label in labels.items():
        item = metrics.get(name)
        if not item:
            continue
        baseline = item.get("baseline")
        enhanced = item.get("enhanced")
        if baseline is None or enhanced is None:
            continue
        result.append(
            "在项目内 benchmark 测试集上，"
            f"{label} 从 {baseline:.2f} 变化到 {enhanced:.2f}。"
        )
    if not result:
        result.append(
            "在项目内 benchmark 测试集上，本次对比未产生可汇总的共同指标。"
        )
    return result
