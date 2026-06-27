import asyncio

import pytest

from app.tools.contracts import ToolContext, ToolSpec
from app.tools.manager import EnterpriseToolManager


class SlowTool:
    spec = ToolSpec(
        name="slow",
        description="Slow tool.",
        input_schema={"type": "object", "properties": {}},
        timeout_ms=1,
    )

    async def run(self, payload, context):
        del payload, context
        await asyncio.sleep(0.05)
        return {"ok": True}


@pytest.mark.asyncio
async def test_tool_manager_timeout_returns_failed_result() -> None:
    manager = EnterpriseToolManager()
    manager.register(SlowTool())

    result = await manager.execute(
        "slow",
        {},
        ToolContext(user_id=1),
    )

    assert result.success is False
    assert result.error_code == "timeout"
    assert result.metadata["tool_timeout"] is True
    assert result.latency_ms >= 0
