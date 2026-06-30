from types import SimpleNamespace
from unittest.mock import Mock

from app.api import chat as chat_module


def test_chat_orchestrator_receives_enabled_runtime_capabilities(
    monkeypatch,
) -> None:
    build_orchestrator = getattr(
        chat_module,
        "build_orchestrator",
        None,
    )
    assert build_orchestrator is not None

    tool_manager = object()
    monitor = object()
    data_service = object()
    state = SimpleNamespace(
        router=object(),
        gateway=object(),
        retrieval=object(),
        data_service_factory=lambda session: data_service,
        long_term_memory=object(),
        tool_manager=tool_manager,
        composite_agent_enabled=True,
        monitoring_service=monitor,
    )
    request = SimpleNamespace(
        app=SimpleNamespace(state=state),
    )
    orchestrator_factory = Mock(return_value=object())
    monkeypatch.setattr(
        chat_module,
        "AgentOrchestrator",
        orchestrator_factory,
    )

    build_orchestrator(request, object())

    kwargs = orchestrator_factory.call_args.kwargs
    assert kwargs["tool_manager"] is tool_manager
    assert kwargs["composite_enabled"] is True
    assert kwargs["monitor"] is monitor
    assert kwargs["data_service"] is data_service

