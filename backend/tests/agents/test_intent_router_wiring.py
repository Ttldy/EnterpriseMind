from app.agents.intent_recognizer import EnterpriseIntentRecognizer
from app.main import create_app
from app.shared.config import get_settings


def test_create_app_uses_hybrid_intent_router_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("INTENT_ROUTER_MODE", "hybrid")
    get_settings.cache_clear()

    app = create_app()

    assert isinstance(app.state.router, EnterpriseIntentRecognizer)
    get_settings.cache_clear()
