import pytest

from app.agents.contracts import Sensitivity
from app.model_gateway.contracts import ModelRequest, ModelResponse
from app.model_gateway.gateway import ModelGateway
from app.monitoring.contracts import MonitorEvent


class RecordingMonitor:
    def __init__(self) -> None:
        self.events: list[MonitorEvent] = []

    def record(self, event: MonitorEvent) -> bool:
        self.events.append(event)
        return True


class Provider:
    def __init__(self, name: str, fail: bool = False) -> None:
        self.name = name
        self.fail = fail

    async def generate(self, request: ModelRequest) -> ModelResponse:
        del request
        if self.fail:
            raise RuntimeError("provider unavailable")
        return ModelResponse(text="ok", model=self.name)


@pytest.mark.asyncio
async def test_gateway_records_external_to_local_fallback_without_prompt() -> None:
    monitor = RecordingMonitor()
    gateway = ModelGateway(
        local=Provider("local"),
        external=Provider("external", fail=True),
        monitor=monitor,
    )

    result = await gateway.generate(
        ModelRequest("secret system prompt", "secret question"),
        Sensitivity.PUBLIC,
    )

    saved = monitor.events[0]
    assert result.provider == "ollama"
    assert saved.provider == "ollama"
    assert saved.model == "local"
    assert saved.fallback is True
    assert saved.metadata == {
        "sensitivity": "public",
        "external_sent": False,
    }

