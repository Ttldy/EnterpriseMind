import pytest

from app.evaluation.contracts import EvaluationCase
from app.evaluation.executor import DemoCaseExecutor


@pytest.mark.asyncio
async def test_demo_case_executor_still_returns_extended_case_output() -> None:
    output = await DemoCaseExecutor().execute(
        EvaluationCase(
            case_id="demo-1",
            category="quality",
            prompt_key="finance_agent",
            question="How to reimburse?",
            expected_agent="finance",
            expected_provider="ollama",
        ),
        "candidate prompt",
    )

    assert output.agent == "finance"
    assert output.provider == "ollama"
    assert output.model is None
    assert output.external_sent is None
