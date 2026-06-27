import pytest

from app.tools.contracts import (
    ToolContext,
    ToolExecutionError,
    ToolSpec,
)
from app.tools.manager import EnterpriseToolManager


class EchoTool:
    spec = ToolSpec(
        name="echo",
        description="Return the input payload.",
    )

    async def run(
        self,
        payload: dict[str, object],
        context: ToolContext,
    ) -> dict[str, object]:
        return {
            "payload": payload,
            "user_id": context.user_id,
        }


class FailingTool:
    spec = ToolSpec(
        name="failing",
        description="Always fails.",
    )

    async def run(
        self,
        payload: dict[str, object],
        context: ToolContext,
    ) -> dict[str, object]:
        del payload, context
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_tool_manager_executes_registered_tool() -> None:
    manager = EnterpriseToolManager()
    manager.register(EchoTool())

    result = await manager.execute(
        "echo",
        {"message": "hello"},
        ToolContext(user_id=7),
    )

    assert result.success is True
    assert result.output == {
        "payload": {"message": "hello"},
        "user_id": 7,
    }
    assert result.metadata["tool_name"] == "echo"


@pytest.mark.asyncio
async def test_tool_manager_converts_tool_error_to_failed_result() -> None:
    manager = EnterpriseToolManager()
    manager.register(FailingTool())

    result = await manager.execute(
        "failing",
        {},
        ToolContext(user_id=7),
    )

    assert result.success is False
    assert result.output is None
    assert isinstance(result.error, ToolExecutionError)
    assert result.metadata["tool_failure"] is True
