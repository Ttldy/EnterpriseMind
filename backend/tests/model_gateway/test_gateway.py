import pytest

from app.agents.contracts import Sensitivity
from app.model_gateway.contracts import (
    ModelRequest,
    ModelResponse,
)
from app.model_gateway.gateway import (
    ModelGateway,
    SensitiveModelUnavailable,
)


class SpyProvider:
    def __init__(
        self,
        name: str,
        fail: bool = False,
    ) -> None:
        self.name = name
        self.fail = fail
        self.calls: list[ModelRequest] = []

    async def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        self.calls.append(request)
        if self.fail:
            raise RuntimeError("provider failed")
        return ModelResponse(
            text="ok",
            model=self.name,
        )


@pytest.mark.asyncio
async def test_public_uses_external() -> None:
    local = SpyProvider("ollama")
    external = SpyProvider("external")
    gateway = ModelGateway(local, external)

    result = await gateway.generate(
        ModelRequest("system", "公开问题"),
        Sensitivity.PUBLIC,
    )

    assert result.provider == "external"
    assert result.external_sent is True
    assert len(external.calls) == 1
    assert local.calls == []


@pytest.mark.asyncio
async def test_public_falls_back_to_local() -> None:
    local = SpyProvider("ollama")
    external = SpyProvider(
        "external",
        fail=True,
    )
    gateway = ModelGateway(local, external)

    result = await gateway.generate(
        ModelRequest("system", "公开问题"),
        Sensitivity.PUBLIC,
    )

    assert result.provider == "ollama"
    assert result.external_sent is False
    assert len(local.calls) == 1


@pytest.mark.asyncio
async def test_sensitive_never_calls_external() -> None:
    local = SpyProvider("ollama")
    external = SpyProvider("external")
    gateway = ModelGateway(local, external)

    result = await gateway.generate(
        ModelRequest("system", "查询工资"),
        Sensitivity.SENSITIVE,
    )

    assert result.provider == "ollama"
    assert result.external_sent is False
    assert external.calls == []


@pytest.mark.asyncio
async def test_sensitive_local_failure_refuses() -> None:
    local = SpyProvider("ollama", fail=True)
    external = SpyProvider("external")
    gateway = ModelGateway(local, external)

    with pytest.raises(SensitiveModelUnavailable):
        await gateway.generate(
            ModelRequest("system", "查询工资"),
            Sensitivity.SENSITIVE,
        )

    assert external.calls == []
