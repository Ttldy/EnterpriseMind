from app.main import create_app
from app.monitoring.service import MonitoringService
from app.shared.config import get_settings


def test_create_app_registers_monitoring_service_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("MONITOR_ENABLED", "true")
    monkeypatch.setenv("TOOL_MANAGER_ENABLED", "true")
    get_settings.cache_clear()

    app = create_app()

    assert isinstance(app.state.monitoring_service, MonitoringService)
    monitor = app.state.monitoring_service
    assert app.state.gateway._monitor is monitor
    assert app.state.retrieval._monitor is monitor
    assert app.state.long_term_memory._monitor is monitor
    assert app.state.tool_manager._monitor is monitor
    data_service = app.state.data_service_factory(object())
    assert data_service._monitor is monitor
    get_settings.cache_clear()


def test_create_app_disables_all_monitor_recorders(monkeypatch) -> None:
    monkeypatch.setenv("MONITOR_ENABLED", "false")
    monkeypatch.setenv("TOOL_MANAGER_ENABLED", "true")
    get_settings.cache_clear()

    app = create_app()

    assert app.state.monitoring_service is None
    assert app.state.gateway._monitor is None
    assert app.state.retrieval._monitor is None
    assert app.state.long_term_memory._monitor is None
    assert app.state.tool_manager._monitor is None
    get_settings.cache_clear()
