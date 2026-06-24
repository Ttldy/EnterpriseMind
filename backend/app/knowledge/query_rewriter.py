import json
from typing import Protocol

from app.agents.contracts import Sensitivity
from app.model_gateway.contracts import GatewayResponse, ModelRequest


class QueryRewriteGateway(Protocol):
    async def generate(
        self,
        request: ModelRequest,
        sensitivity: Sensitivity,
    ) -> GatewayResponse: ...


class QueryRewriter:
    def __init__(
        self,
        gateway: QueryRewriteGateway,
    ) -> None:
        self._gateway = gateway

    async def rewrite(
        self,
        query: str,
    ) -> list[str]:
        prompt = (
            "你是企业知识库检索查询改写器。"
            "请把用户问题改写成 2 到 4 个等价检索 query。"
            "不得改变人名、金额、日期、部门、系统名。"
            "只返回 JSON 数组字符串。"
        )
        try:
            response = await self._gateway.generate(
                ModelRequest(
                    system_prompt=prompt,
                    user_message=query,
                ),
                Sensitivity.INTERNAL,
            )
            values = json.loads(response.text)
        except Exception:
            return [query]

        if not isinstance(values, list):
            return [query]

        rewritten = [
            str(item).strip()
            for item in values
            if isinstance(item, str) and item.strip()
        ]
        return _dedupe([query, *rewritten])


class NoopQueryRewriter:
    async def rewrite(
        self,
        query: str,
    ) -> list[str]:
        return [query]


def _dedupe(
    values: list[str],
) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
