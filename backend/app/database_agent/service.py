import json
from dataclasses import dataclass
from typing import Protocol

from app.agents.contracts import Sensitivity
from app.database_agent.generator import (
    SqlGenerator,
)
from app.database_agent.repository import (
    DatasetLoader,
    DatasetPolicy,
)
from app.database_agent.validator import (
    SqlPolicy,
    validate_sql,
)
from app.knowledge.access import AccessContext
from app.model_gateway.contracts import (
    ModelRequest,
)
from app.model_gateway.gateway import ModelGateway


class SqlExecutor(Protocol):
    async def execute(
        self,
        sql: str,
    ) -> list[dict[str, object]]: ...


@dataclass(frozen=True)
class DataQueryResult:
    answer: str
    sql: str
    row_count: int
    model: str
    provider: str
    route_reason: str
    external_sent: bool


class DataQueryService:
    def __init__(
        self,
        datasets: DatasetLoader,
        generator: SqlGenerator,
        executor: SqlExecutor,
        gateway: ModelGateway,
        max_rows: int = 200,
    ) -> None:
        self._datasets = datasets
        self._generator = generator
        self._executor = executor
        self._gateway = gateway
        self._max_rows = max_rows

    async def answer(
        self,
        question: str,
        access: AccessContext,
    ) -> DataQueryResult:
        datasets = await self._datasets.list_authorized(access)
        dataset = self._select_dataset(
            question,
            datasets,
        )
        if dataset is None:
            raise PermissionError("没有可用于该问题的授权数据集")

        raw_sql, generation = await self._generator.generate(
            question,
            dataset,
        )
        safe_sql = validate_sql(
            raw_sql,
            SqlPolicy(
                views=frozenset({dataset.view_name}),
                columns=dataset.allowed_columns,
                max_rows=self._max_rows,
            ),
        )
        rows = await self._executor.execute(safe_sql)

        explanation = await self._gateway.generate(
            ModelRequest(
                system_prompt=(
                    "你是企业数据分析助手。"
                    "只能根据给定查询结果回答，"
                    "不得补充结果中不存在的数据。"
                    "用简洁中文说明结论。"
                ),
                user_message=(
                    f"问题：{question}\n"
                    f"SQL：{safe_sql}\n"
                    "结果："
                    + json.dumps(
                        rows,
                        ensure_ascii=False,
                        default=str,
                    )
                ),
            ),
            Sensitivity.SENSITIVE,
        )

        return DataQueryResult(
            answer=explanation.text,
            sql=safe_sql,
            row_count=len(rows),
            model=explanation.model,
            provider=explanation.provider,
            route_reason=(explanation.route_reason),
            external_sent=(generation.external_sent or explanation.external_sent),
        )

    @staticmethod
    def _select_dataset(
        question: str,
        datasets: list[DatasetPolicy],
    ) -> DatasetPolicy | None:
        normalized = question.lower()
        ranked = sorted(
            datasets,
            key=lambda dataset: sum(
                1 for keyword in dataset.keywords if keyword.lower() in normalized
            ),
            reverse=True,
        )
        if not ranked:
            return None

        best = ranked[0]
        score = sum(1 for keyword in best.keywords if keyword.lower() in normalized)
        return best if score > 0 else None
