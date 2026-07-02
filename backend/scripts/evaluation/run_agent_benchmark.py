from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from app.evaluation.benchmark_contracts import BenchmarkProfile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run EnterpriseMind Agent benchmark."
    )
    parser.add_argument(
        "--profile",
        choices=("baseline", "enhanced"),
        required=True,
    )
    parser.add_argument(
        "--output",
        required=True,
        help="UTF-8 JSON output path.",
    )
    parser.add_argument(
        "--cases",
        default="evaluation/cases",
        help="Benchmark case directory.",
    )
    return parser.parse_args()


def profile_from_name(
    name: str,
) -> BenchmarkProfile:
    if name == "baseline":
        return BenchmarkProfile.baseline()
    return BenchmarkProfile.enhanced()


async def run() -> None:
    args = parse_args()
    profile = profile_from_name(args.profile)
    os.environ.update(profile.settings)

    from app.evaluation.benchmark_runner import BenchmarkRunner
    from app.evaluation.judge import LLMJudgeScorer
    from app.evaluation.orchestrator_executor import OrchestratorCaseExecutor
    from app.evaluation.prompt_service import PromptService
    from app.evaluation.resolver import DatabasePromptResolver
    from app.main import create_app
    from app.shared.config import get_settings
    from app.shared.database import SessionFactory

    settings = get_settings()
    # Benchmark events are evaluated by the controlled fixture below and must
    # not pollute the online PostgreSQL monitoring window.
    settings.monitor_enabled = False
    app = create_app()
    output = Path(args.output)
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    async with app.router.lifespan_context(app):
        async with SessionFactory() as session:
            executor = OrchestratorCaseExecutor(
                session=session,
                router=app.state.router,
                gateway=app.state.gateway,
                retrieval=app.state.retrieval,
                data_service=(
                    app.state.data_service_factory(session)
                ),
                prompts=DatabasePromptResolver(
                    PromptService(session)
                ),
                memory=app.state.long_term_memory,
                tool_manager=app.state.tool_manager,
                composite_enabled=(
                    app.state.composite_agent_enabled
                ),
                monitor=app.state.monitoring_service,
                default_usernames={
                    "hr_agent": (
                        settings.evaluation_default_hr_username
                    ),
                    "it_agent": (
                        settings.evaluation_default_it_username
                    ),
                    "finance_agent": (
                        settings.evaluation_default_finance_username
                    ),
                    "data_analyst_agent": (
                        settings.evaluation_default_finance_username
                    ),
                    "employee": (
                        settings.evaluation_default_employee_username
                    ),
                    "admin": (
                        settings.evaluation_default_admin_username
                    ),
                },
            )
            judge = (
                LLMJudgeScorer(
                    app.state.gateway,
                    minimum_score=(
                        settings.benchmark_judge_minimum_score
                    ),
                )
                if settings.benchmark_judge_enabled
                else None
            )
            report = await BenchmarkRunner(
                executor=executor,
                case_directory=Path(args.cases),
                prompt_content="EnterpriseMind benchmark candidate prompt",
                judge=judge,
                judge_enabled=(
                    settings.benchmark_judge_enabled
                ),
            ).run(profile)

    output.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "profile": profile.name,
                "case_count": report["case_count"],
                "output": str(output),
                "metrics": report["metrics"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(run())
