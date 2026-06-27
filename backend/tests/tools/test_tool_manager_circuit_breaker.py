import pytest

from app.tools.contracts import ToolContext, ToolSpec
from app.tools.manager import EnterpriseToolManager


class FlakyTool:
    def __init__(self) -> None:
        self.calls = 0
        self.should_fail = True
        self.spec = ToolSpec(
            name="flaky",
            description="Flaky tool.",
            input_schema={"type": "object", "properties": {}},
            circuit_breaker_enabled=True,
        )

    async def run(self, payload, context):
        del payload, context
        self.calls += 1
        if self.should_fail:
            raise RuntimeError("boom")
        return {"ok": True}


@pytest.mark.asyncio
async def test_circuit_opens_after_failure_threshold_and_skips_underlying_tool() -> None:
    tool = FlakyTool()
    manager = EnterpriseToolManager(
        circuit_failure_threshold=3,
        circuit_recovery_seconds=30,
    )
    manager.register(tool)
    context = ToolContext(user_id=1)

    for _ in range(3):
        result = await manager.execute("flaky", {}, context)
        assert result.success is False

    open_result = await manager.execute("flaky", {}, context)

    assert open_result.success is False
    assert open_result.circuit_open is True
    assert open_result.error_code == "circuit_open"
    assert tool.calls == 3


@pytest.mark.asyncio
async def test_circuit_half_open_success_recovers() -> None:
    tool = FlakyTool()
    manager = EnterpriseToolManager(
        circuit_failure_threshold=1,
        circuit_recovery_seconds=0,
    )
    manager.register(tool)
    context = ToolContext(user_id=1)

    failed = await manager.execute("flaky", {}, context)
    assert failed.success is False

    tool.should_fail = False
    recovered = await manager.execute("flaky", {}, context)
    next_result = await manager.execute("flaky", {}, context)

    assert recovered.success is True
    assert recovered.circuit_open is False
    assert next_result.success is True
