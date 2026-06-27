from app.agents.contracts import Sensitivity
from app.tools.contracts import ToolContext, ToolResult, ToolSpec


def test_tool_spec_exposes_mcp_like_contract_fields() -> None:
    spec = ToolSpec(
        name="knowledge_search",
        description="Search knowledge.",
        input_schema={
            "type": "object",
            "required": ["query"],
            "properties": {"query": {"type": "string"}},
        },
        timeout_ms=1500,
        cache_ttl_seconds=30,
        cache_enabled=True,
        circuit_breaker_enabled=True,
        fallback_enabled=True,
        required_roles=frozenset({"employee"}),
        sensitivity=Sensitivity.INTERNAL,
    )

    assert spec.input_schema["required"] == ["query"]
    assert spec.timeout_ms == 1500
    assert spec.cache_ttl_seconds == 30
    assert spec.cache_enabled is True
    assert spec.circuit_breaker_enabled is True
    assert spec.fallback_enabled is True
    assert spec.required_roles == frozenset({"employee"})
    assert spec.sensitivity is Sensitivity.INTERNAL


def test_tool_context_contains_trace_and_request_ids() -> None:
    context = ToolContext(
        user_id=7,
        department="IT",
        roles=frozenset({"employee"}),
        trace_id="trace-1",
        request_id="request-1",
    )

    assert context.trace_id == "trace-1"
    assert context.request_id == "request-1"


def test_tool_result_exposes_runtime_metadata_fields() -> None:
    result = ToolResult(
        success=False,
        output=None,
        error_code="timeout",
        error_message="tool timed out",
        latency_ms=1000,
        cache_hit=False,
        circuit_open=False,
        fallback_used=True,
        sensitivity=Sensitivity.INTERNAL,
    )

    assert result.error_code == "timeout"
    assert result.error_message == "tool timed out"
    assert result.latency_ms == 1000
    assert result.cache_hit is False
    assert result.circuit_open is False
    assert result.fallback_used is True
    assert result.sensitivity is Sensitivity.INTERNAL
