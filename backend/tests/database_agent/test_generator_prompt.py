import pytest

from app.agents.contracts import Sensitivity
from app.database_agent.generator import SqlGenerator
from app.database_agent.repository import DatasetPolicy
from app.model_gateway.contracts import (
    GatewayResponse,
    ModelRequest,
)
from scripts.http_demo.chat_scenario import SCENARIOS


class CapturingGateway:
    def __init__(self) -> None:
        self.request: ModelRequest | None = None

    async def generate(
        self,
        request: ModelRequest,
        sensitivity: Sensitivity,
    ) -> GatewayResponse:
        self.request = request
        return GatewayResponse(
            text=("SELECT department, total_amount " "FROM expense_summary_view"),
            model="test-model",
            provider="ollama",
            route_reason="sensitive_requires_local",
            external_sent=False,
        )


@pytest.mark.asyncio
async def test_prompt_forbids_invented_filters() -> None:
    gateway = CapturingGateway()
    dataset = DatasetPolicy(
        id=1,
        name="expense_summary",
        view_name="expense_summary_view",
        description="报销汇总",
        schema_text=(
            "expense_summary_view(" "department text, month text, " "total_amount numeric)"
        ),
        sensitivity="sensitive",
        allowed_columns=frozenset({"department", "month", "total_amount"}),
        keywords=("报销统计",),
    )

    await SqlGenerator(gateway).generate(
        "统计2026年6月各部门报销金额",
        dataset,
    )

    assert gateway.request is not None
    assert "禁止猜测用户未提供的月份" in (gateway.request.system_prompt)
    assert "没有明确指定筛选条件时，禁止添加 WHERE" in (gateway.request.system_prompt)


def test_data_scenario_matches_seed_month() -> None:
    assert "2026年6月" in SCENARIOS["data"]
    assert "2026年6月" in SCENARIOS["unauthorized-data"]
