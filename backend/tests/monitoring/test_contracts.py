from app.monitoring.contracts import MonitorEvent


def test_monitor_event_sanitizes_metadata_and_clamps_latency() -> None:
    event = MonitorEvent(
        component="retrieval",
        operation="retrieve",
        success=True,
        latency_ms=-5,
        metadata={
            "query_count": 3,
            "evidence_level": "full",
            "question": "VPN 无法连接怎么办？",
            "answer": "完整回答",
            "prompt": "system prompt",
            "chunk": "raw chunk",
            "sql": "SELECT secret FROM payroll",
            "sql_result": [{"salary": 10000}],
            "authorization": "Bearer secret",
            "nested": {"token": "secret"},
        },
    )

    assert event.latency_ms == 0
    assert event.metadata == {
        "query_count": 3,
        "evidence_level": "full",
    }


def test_monitor_event_truncates_allowed_string_metadata() -> None:
    event = MonitorEvent(
        component="data_query",
        operation="answer",
        success=True,
        latency_ms=1,
        metadata={"business_outcome": "x" * 300},
    )

    assert event.metadata["business_outcome"] == "x" * 120

