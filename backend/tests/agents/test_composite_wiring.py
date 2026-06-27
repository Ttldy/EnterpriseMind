from app.main import create_app
from app.shared.config import get_settings


def test_create_app_marks_composite_enabled_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("COMPOSITE_AGENT_ENABLED", "true")
    get_settings.cache_clear()

    app = create_app()

    assert app.state.composite_agent_enabled is True
    get_settings.cache_clear()
