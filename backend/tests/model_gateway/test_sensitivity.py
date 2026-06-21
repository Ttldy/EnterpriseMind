from app.agents.contracts import Sensitivity
from app.model_gateway.sensitivity import (
    classify_question,
    highest_sensitivity,
)


def test_sensitive_keyword_wins() -> None:
    decision = classify_question("帮我统计员工工资")

    assert decision.level is Sensitivity.SENSITIVE


def test_unknown_level_fails_closed() -> None:
    result = highest_sensitivity(
        Sensitivity.PUBLIC,
        "unexpected-level",
    )

    assert result is Sensitivity.SENSITIVE


def test_highest_level_is_selected() -> None:
    result = highest_sensitivity(
        Sensitivity.PUBLIC,
        Sensitivity.INTERNAL,
        Sensitivity.SENSITIVE,
    )

    assert result is Sensitivity.SENSITIVE
