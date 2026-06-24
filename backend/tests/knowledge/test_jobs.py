from app.knowledge.job_service import (
    can_retry,
    job_key,
)


def test_job_key_is_deterministic() -> None:
    first = job_key(7, "abc")
    second = job_key(7, "abc")
    assert first == second
    assert first == "document:7:abc"


def test_retry_stops_after_three_attempts() -> None:
    assert can_retry(0) is True
    assert can_retry(2) is True
    assert can_retry(3) is False