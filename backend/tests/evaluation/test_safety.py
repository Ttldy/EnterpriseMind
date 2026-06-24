from app.evaluation.contracts import (
    SafetyReport,
)
from app.evaluation.safety import SafetyEvaluator


def test_safety_requires_every_case() -> None:
    report: SafetyReport = (
        SafetyEvaluator.summarize(
            [True, True, False]
        )
    )
    assert report.pass_rate == 2 / 3
    assert report.release_allowed is False


def test_empty_safety_set_is_blocked() -> None:
    report = SafetyEvaluator.summarize([])
    assert report.release_allowed is False