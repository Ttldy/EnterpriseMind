import pytest

from app.agents.contracts import Sensitivity
from app.knowledge.query_rewriter import NoopQueryRewriter, QueryRewriter
from app.model_gateway.contracts import GatewayResponse


class RewriteGateway:
    def __init__(self, text: str = "[]", fail: bool = False) -> None:
        self.text = text
        self.fail = fail
        self.sensitivity: Sensitivity | None = None

    async def generate(self, request, sensitivity):
        del request
        self.sensitivity = sensitivity
        if self.fail:
            raise RuntimeError("model unavailable")
        return GatewayResponse(
            text=self.text,
            provider="local",
            model="test",
            external_sent=False,
            route_reason="test",
        )


@pytest.mark.asyncio
async def test_rewriter_returns_variants_without_original() -> None:
    gateway = RewriteGateway('["VPN 无法连接", "VPN 连接失败"]')

    values = await QueryRewriter(gateway).rewrite("VPN 无法连接")

    assert values == ["VPN 连接失败"]
    assert gateway.sensitivity == Sensitivity.INTERNAL


@pytest.mark.asyncio
async def test_rewriter_failure_and_noop_return_no_variants() -> None:
    failed = await QueryRewriter(RewriteGateway(fail=True)).rewrite("VPN")
    noop = await NoopQueryRewriter().rewrite("VPN")

    assert failed == []
    assert noop == []

