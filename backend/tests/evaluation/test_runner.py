from app.evaluation.runner import compare_metrics


def test_quality_regression_blocks_release() -> None:
    result = compare_metrics(
        baseline={
            "answer_accuracy": 0.88,
            "citation_accuracy": 0.93,
        },
        candidate={
            "answer_accuracy": 0.82,
            "citation_accuracy": 0.94,
        },
    )
    assert result.release_allowed is False
    assert result.regressions == (
        "answer_accuracy",
    )


def test_small_drop_is_allowed() -> None:
    result = compare_metrics(
        {"answer_accuracy": 0.88},
        {"answer_accuracy": 0.86},
    )
    assert result.release_allowed is True