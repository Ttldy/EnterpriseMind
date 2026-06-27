from app.main import create_app
from app.shared.config import get_settings
from app.tools.manager import EnterpriseToolManager


def test_create_app_registers_tool_manager_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("TOOL_MANAGER_ENABLED", "true")
    get_settings.cache_clear()

    app = create_app()

    assert isinstance(app.state.tool_manager, EnterpriseToolManager)
    get_settings.cache_clear()
