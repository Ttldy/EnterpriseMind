import pytest

from app.agents.contracts import Sensitivity
from app.database_agent.repository import (
    DatasetPolicy,
)
from app.database_agent.service import (
    DataQueryService,
)
from app.knowledge.access import AccessContext
from app.model_gateway.contracts import (
    GatewayResponse,
)

EXPENSE_DATASET = DatasetPolicy(
    id=3,
    name="expense_summary",
    view_name="expense_summary_view",
    description="报销汇总",
    schema_text=("expense_summary_view(" "department text, " "total_amount numeric)"),
    sensitivity="sensitive",
    allowed_columns=frozenset({"department", "total_amount"}),
    keywords=("报销统计", "各部门报销"),
)


class FakeDatasets:
    def __init__(
        self,
        values: list[DatasetPolicy],
    ) -> None:
        self.values = values

    async def list_authorized(
        self,
        access: AccessContext,
    ) -> list[DatasetPolicy]:
        return self.values


class FakeGenerator:
    async def generate(
        self,
        question: str,
        dataset: DatasetPolicy,
        memory_context: str = "",
    ):
        del memory_context
        return (
            (
                "SELECT department, "
                "SUM(total_amount) AS total_amount "
                "FROM expense_summary_view "
                "GROUP BY department"
            ),
            GatewayResponse(
                text="sql",
                model="local-test",
                provider="ollama",
                route_reason=("sensitive_requires_local"),
                external_sent=False,
            ),
        )


class FakeExecutor:
    async def execute(
        self,
        sql: str,
    ) -> list[dict[str, object]]:
        return [
            {
                "department": "IT",
                "total_amount": 8500,
            }
        ]


class FakeGateway:
    async def generate(
        self,
        request,
        sensitivity: Sensitivity,
    ) -> GatewayResponse:
        assert sensitivity is Sensitivity.SENSITIVE
        return GatewayResponse(
            text="IT 部门报销 8500 元。",
            model="local-test",
            provider="ollama",
            route_reason=("sensitive_requires_local"),
            external_sent=False,
        )


FINANCE_ACCESS = AccessContext(
    user_id=5,
    department="FINANCE",
    roles=frozenset({"employee", "finance_staff"}),
    knowledge_base_ids=frozenset(),
    dataset_ids=frozenset({3}),
)


@pytest.mark.asyncio
async def test_authorized_query_executes() -> None:
    service = DataQueryService(
        datasets=FakeDatasets([EXPENSE_DATASET]),
        generator=FakeGenerator(),
        executor=FakeExecutor(),
        gateway=FakeGateway(),
    )

    result = await service.answer(
        "统计各部门报销金额",
        FINANCE_ACCESS,
    )

    assert result.row_count == 1
    assert result.provider == "ollama"
    assert result.external_sent is False
    assert result.sql.endswith("LIMIT 200")


@pytest.mark.asyncio
async def test_no_authorized_dataset_refuses() -> None:
    service = DataQueryService(
        datasets=FakeDatasets([]),
        generator=FakeGenerator(),
        executor=FakeExecutor(),
        gateway=FakeGateway(),
    )

    with pytest.raises(PermissionError):
        await service.answer(
            "统计各部门报销金额",
            FINANCE_ACCESS,
        )
