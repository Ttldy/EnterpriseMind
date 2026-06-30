from app.shared.config import Settings


def test_agent_engineering_capabilities_are_enabled_by_default() -> None:
    fields = Settings.model_fields

    assert fields["intent_router_mode"].default == "hybrid"
    assert fields["tool_manager_enabled"].default is True
    assert fields["composite_agent_enabled"].default is True
    assert fields["monitor_enabled"].default is True

