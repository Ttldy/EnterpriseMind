from app.main import create_app
from app.monitoring.service import MonitoringService
from app.shared.config import get_settings


def test_create_app_registers_monitoring_service_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("MONITOR_ENABLED", "true")
    get_settings.cache_clear()

    app = create_app()

    assert isinstance(app.state.monitoring_service, MonitoringService)
    get_settings.cache_clear()
