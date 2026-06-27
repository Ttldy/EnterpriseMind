import pytest

from app.tools.contracts import ToolContext, ToolSpec
from app.tools.manager import EnterpriseToolManager


class SchemaTool:
    spec = ToolSpec(
        name="schema_tool",
        description="Schema validation tool.",
        input_schema={
            "type": "object",
            "required": ["query", "limit"],
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
    )

    async def run(self, payload, context):
        del context
        return {"ok": payload}


@pytest.mark.asyncio
async def test_tool_manager_returns_validation_error_for_missing_required_field() -> None:
    manager = EnterpriseToolManager()
    manager.register(SchemaTool())

    result = await manager.execute(
        "schema_tool",
        {"query": "vpn"},
        ToolContext(user_id=1),
    )

    assert result.success is False
    assert result.error_code == "validation_error"
    assert "limit" in (result.error_message or "")
    assert result.metadata["tool_validation_error"] is True


@pytest.mark.asyncio
async def test_tool_manager_returns_validation_error_for_wrong_type() -> None:
    manager = EnterpriseToolManager()
    manager.register(SchemaTool())

    result = await manager.execute(
        "schema_tool",
        {"query": "vpn", "limit": "5"},
        ToolContext(user_id=1),
    )

    assert result.success is False
    assert result.error_code == "validation_error"
    assert "limit" in (result.error_message or "")
    assert result.metadata["tool_validation_error"] is True
