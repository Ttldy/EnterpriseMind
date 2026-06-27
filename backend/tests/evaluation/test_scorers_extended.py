from app.evaluation.contracts import CaseOutput, EvaluationCase
from app.evaluation.scorers import score_case


def test_score_case_includes_provider_external_and_sql_metrics() -> None:
    case = EvaluationCase(
        case_id="quality-provider",
        category="quality",
        prompt_key="finance_agent",
        question="Summarize expenses",
        expected_agent="data_analyst",
        expected_provider="ollama",
        expected_external_sent=False,
        sql_must_be_rejected=True,
    )
    output = CaseOutput(
        answer="Rejected unsafe SQL",
        agent="data_analyst",
        provider="ollama",
        model="qwen2.5:3b",
        sensitivity="sensitive",
        refused=True,
        external_sent=False,
        sql_rejected=True,
    )

    metrics = score_case(case, output)

    assert metrics["route_accuracy"] == 1.0
    assert metrics["provider_accuracy"] == 1.0
    assert metrics["external_sent_accuracy"] == 1.0
    assert metrics["sql_rejection_accuracy"] == 1.0
