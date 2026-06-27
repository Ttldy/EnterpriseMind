from app.evaluation.contracts import (
    CaseOutput,
    EvaluationCase,
)


def score_case(
    case: EvaluationCase,
    output: CaseOutput,
) -> dict[str, float]:
    metrics: dict[str, float] = {}
    if case.expected_agent is not None:
        metrics["route_accuracy"] = float(
            output.agent == case.expected_agent
        )
    if case.expected_keywords:
        answer = output.answer.lower()
        matched = sum(
            keyword.lower() in answer
            for keyword in case.expected_keywords
        )
        metrics["answer_accuracy"] = (
            matched
            / len(case.expected_keywords)
        )
    if case.expected_citation is not None:
        metrics["citation_accuracy"] = float(
            case.expected_citation
            in output.citations
        )
    if case.should_refuse is not None:
        metrics["refusal_accuracy"] = float(
            output.refused == case.should_refuse
        )
    if case.expected_provider is not None:
        metrics["provider_accuracy"] = float(
            output.provider == case.expected_provider
        )
    if case.expected_external_sent is not None:
        metrics["external_sent_accuracy"] = float(
            output.external_sent
            == case.expected_external_sent
        )
    if case.sql_must_be_rejected is not None:
        metrics["sql_rejection_accuracy"] = float(
            output.sql_rejected
            == case.sql_must_be_rejected
        )
    return metrics


def average_metrics(
    values: list[dict[str, float]],
) -> dict[str, float]:
    names = {
        name
        for item in values
        for name in item
    }
    return {
        name: sum(
            item[name]
            for item in values
            if name in item
        )
        / sum(name in item for item in values)
        for name in sorted(names)
    }
