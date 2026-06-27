import pytest

from app.agents.contracts import Sensitivity
from app.tools.contracts import ToolContext, ToolSpec
from app.tools.manager import EnterpriseToolManager


class CountingTool:
    def __init__(self, sensitivity: Sensitivity = Sensitivity.INTERNAL) -> None:
        self.calls = 0
        self.spec = ToolSpec(
            name="counting",
            description="Counting tool.",
            input_schema={
                "type": "object",
                "required": ["query"],
                "properties": {"query": {"type": "string"}},
            },
            cache_enabled=True,
            cache_ttl_seconds=60,
            sensitivity=sensitivity,
        )

    async def run(self, payload, context):
        del context
        self.calls += 1
        return {"query": payload["query"], "calls": self.calls}


@pytest.mark.asyncio
async def test_tool_manager_cache_hit_does_not_call_underlying_tool() -> None:
    tool = CountingTool()
    manager = EnterpriseToolManager()
    manager.register(tool)
    context = ToolContext(
        user_id=1,
        department="IT",
        roles=frozenset({"employee"}),
    )

    first = await manager.execute("counting", {"query": "vpn"}, context)
    second = await manager.execute("counting", {"query": "vpn"}, context)

    assert first.cache_hit is False
    assert second.cache_hit is True
    assert second.output == first.output
    assert tool.calls == 1


@pytest.mark.asyncio
async def test_tool_manager_cache_key_includes_user_department_and_roles() -> None:
    tool = CountingTool()
    manager = EnterpriseToolManager()
    manager.register(tool)

    await manager.execute(
        "counting",
        {"query": "vpn"},
        ToolContext(user_id=1, department="IT", roles=frozenset({"employee"})),
    )
    await manager.execute(
        "counting",
        {"query": "vpn"},
        ToolContext(user_id=2, department="IT", roles=frozenset({"employee"})),
    )
    await manager.execute(
        "counting",
        {"query": "vpn"},
        ToolContext(user_id=1, department="HR", roles=frozenset({"employee"})),
    )

    assert tool.calls == 3


@pytest.mark.asyncio
async def test_sensitive_tool_is_not_cached_by_default() -> None:
    tool = CountingTool(sensitivity=Sensitivity.SENSITIVE)
    manager = EnterpriseToolManager()
    manager.register(tool)
    context = ToolContext(user_id=1)

    first = await manager.execute("counting", {"query": "salary"}, context)
    second = await manager.execute("counting", {"query": "salary"}, context)

    assert first.cache_hit is False
    assert second.cache_hit is False
    assert tool.calls == 2
