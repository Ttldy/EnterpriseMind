import pytest

from app.evaluation.benchmark_contracts import BenchmarkProfile
from app.evaluation.benchmark_runner import BenchmarkRunner
from app.evaluation.contracts import CaseOutput
from app.evaluation.judge import JudgeResult


class FakeExecutor:
    def __init__(self) -> None:
        self.questions: list[str] = []

    async def execute(self, case, prompt_content: str) -> CaseOutput:
        self.questions.append(case.question)
        return CaseOutput(
            answer=(
                "请检查 VPN 客户端、网络、账号状态；"
                "危险 SQL 已拒绝；工具缓存命中。"
            ),
            agent="it",
            intent="knowledge_query",
            provider="ollama",
            refused=case.should_refuse is True,
            sensitivity="internal",
            external_sent=False,
            sql_rejected=case.sql_must_be_rejected,
            metadata={
                "tool_success": True,
                "tool_cache_hit": True,
                "monitor_warning_detected": True,
                "monitor_penalty_delta": 0.2,
            },
        )


class FakeJudge:
    async def score(self, case, output) -> JudgeResult:
        return JudgeResult(
            enabled=True,
            available=True,
            scores={
                "relevance": 1.0,
                "accuracy": 0.8,
                "completeness": 0.9,
                "usefulness": 0.7,
            },
            overall_score=0.85,
            reasons=["回答覆盖 VPN 排查步骤"],
            improvement_suggestions=["可以补充工单入口"],
        )


@pytest.mark.asyncio
async def test_benchmark_runner_loads_cases_and_aggregates_metrics(tmp_path) -> None:
    case_dir = tmp_path / "cases"
    case_dir.mkdir()
    (case_dir / "intent.jsonl").write_text(
        (
            '{"case_id":"intent-it","category":"quality",'
            '"benchmark_module":"intent","prompt_key":"it_agent",'
            '"question":"vpn 无法连接怎么办","expected_agent":"it",'
            '"expected_intent":"knowledge_query",'
            '"expected_sensitivity":"internal",'
            '"expected_keywords":["VPN","账号"],'
            '"expected_external_sent":false}\n'
        ),
        encoding="utf-8",
    )
    (case_dir / "tools.jsonl").write_text(
        (
            '{"case_id":"tool-cache","category":"quality",'
            '"benchmark_module":"tools","prompt_key":"it_agent",'
            '"question":"再次查询 vpn 无法连接怎么办",'
            '"expected_tool_success":true,'
            '"expected_tool_cache_hit":true}\n'
        ),
        encoding="utf-8",
    )
    (case_dir / "composite.jsonl").write_text(
        "",
        encoding="utf-8",
    )
    (case_dir / "monitoring.jsonl").write_text(
        (
            '{"case_id":"monitor-warning","category":"quality",'
            '"benchmark_module":"monitoring","prompt_key":"it_agent",'
            '"question":"模拟工具延迟升高",'
            '"expected_monitor_warning":true}\n'
        ),
        encoding="utf-8",
    )

    report = await BenchmarkRunner(
        executor=FakeExecutor(),
        case_directory=case_dir,
        prompt_content="benchmark prompt",
    ).run(BenchmarkProfile.enhanced())

    assert report["profile"] == "enhanced"
    assert report["case_count"] == 3
    assert report["metrics"]["route_accuracy"] == 1.0
    assert report["metrics"]["intent_accuracy"] == 1.0
    assert report["metrics"]["sensitivity_accuracy"] == 1.0
    assert report["metrics"]["tool_success_rate"] == 1.0
    assert report["metrics"]["tool_cache_hit_rate"] == 1.0
    assert report["metrics"]["monitor_warning_detection_accuracy"] == 1.0
    assert report["metrics"]["external_sent_accuracy"] == 1.0
    assert report["case_results"][0]["benchmark_module"] == "intent"


@pytest.mark.asyncio
async def test_benchmark_runner_can_include_judge_metrics(tmp_path) -> None:
    case_dir = tmp_path / "cases"
    case_dir.mkdir()
    (case_dir / "intent.jsonl").write_text(
        (
            '{"case_id":"intent-it","category":"quality",'
            '"benchmark_module":"intent","prompt_key":"it_agent",'
            '"question":"vpn 无法连接怎么办","expected_agent":"it",'
            '"judge_enabled":true}\n'
        ),
        encoding="utf-8",
    )

    report = await BenchmarkRunner(
        executor=FakeExecutor(),
        case_directory=case_dir,
        prompt_content="benchmark prompt",
        judge=FakeJudge(),
        judge_enabled=True,
    ).run(BenchmarkProfile.enhanced())

    assert report["metrics"]["judge_overall"] == 0.85
    assert report["metrics"]["judge_completeness"] == 0.9
    assert report["case_results"][0]["reasons"] == ["回答覆盖 VPN 排查步骤"]
    assert report["case_results"][0]["improvement_suggestions"] == [
        "可以补充工单入口"
    ]


def test_benchmark_profile_exposes_expected_feature_switches() -> None:
    baseline = BenchmarkProfile.baseline()
    enhanced = BenchmarkProfile.enhanced()

    assert baseline.settings == {
        "INTENT_ROUTER_MODE": "rule",
        "TOOL_MANAGER_ENABLED": "false",
        "COMPOSITE_AGENT_ENABLED": "false",
        "MONITOR_ENABLED": "false",
    }
    assert enhanced.settings == {
        "INTENT_ROUTER_MODE": "hybrid",
        "TOOL_MANAGER_ENABLED": "true",
        "COMPOSITE_AGENT_ENABLED": "true",
        "MONITOR_ENABLED": "true",
    }
