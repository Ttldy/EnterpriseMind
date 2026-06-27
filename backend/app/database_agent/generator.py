import re

from app.agents.contracts import Sensitivity
from app.database_agent.repository import (
    DatasetPolicy,
)
from app.model_gateway.contracts import (
    GatewayResponse,
    ModelRequest,
)
from app.model_gateway.gateway import ModelGateway


class SqlGenerationError(ValueError):
    pass


class SqlGenerator:
    def __init__(
        self,
        gateway: ModelGateway,
    ) -> None:
        self._gateway = gateway

    async def generate(
        self,
        question: str,
        dataset: DatasetPolicy,
        memory_context: str = "",
    ) -> tuple[str, GatewayResponse]:
        prompt = (
            "你是 PostgreSQL 只读 SQL 生成器。\n"
            "只能输出一条 SELECT 或 WITH...SELECT。\n"
            "禁止输出解释、Markdown、注释和分号。\n"
            "禁止 SELECT *。\n"
            "只允许使用给定视图和字段。\n"
            "统计数量使用 COUNT(1)。\n"
            "月份格式是 YYYY-MM。\n"
            "禁止猜测用户未提供的月份、部门或其他筛选条件。\n"
            "用户没有明确指定筛选条件时，禁止添加 WHERE。\n"
            "用户指定中文月份时，将其转换为 YYYY-MM。\n\n"
            f"授权 Schema：\n{dataset.schema_text}"
        )
        response = await self._gateway.generate(
            ModelRequest(
                system_prompt=prompt,
                user_message=(
                    f"{memory_context}\n\n用户问题：{question}"
                    if memory_context
                    else question
                ),
            ),
            Sensitivity.SENSITIVE,
        )
        return (
            extract_sql(response.text),
            response,
        )


def extract_sql(text: str) -> str:
    stripped = text.strip()
    markdown_fence = chr(96) * 3
    fenced = re.search(
        (rf"{markdown_fence}" r"(?:sql)?\s*(.*?)" rf"{markdown_fence}"),
        stripped,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if fenced:
        stripped = fenced.group(1).strip()

    stripped = stripped.rstrip(";").strip()
    lowered = stripped.lower()
    if not (lowered.startswith("select ") or lowered.startswith("with ")):
        raise SqlGenerationError("模型没有生成只读 SQL")
    return stripped
