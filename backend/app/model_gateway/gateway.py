from app.agents.contracts import Sensitivity
from app.model_gateway.contracts import (
    GatewayResponse,
    ModelProvider,
    ModelRequest,
)


class SensitiveModelUnavailable(RuntimeError):
    pass


class ModelGateway:
    def __init__(
        self,
        local: ModelProvider,
        external: ModelProvider,
        allow_external_for_internal: bool = False,
    ) -> None:
        self._local = local
        self._external = external
        self._allow_external_for_internal = allow_external_for_internal

    async def generate(
        self,
        request: ModelRequest,
        sensitivity: Sensitivity,
    ) -> GatewayResponse:
        if sensitivity is Sensitivity.PUBLIC:
            return await self._external_then_local(request)

        if sensitivity is Sensitivity.INTERNAL and self._allow_external_for_internal:
            return await self._external_then_local(request)

        return await self._local_only(
            request=request,
            sensitivity=sensitivity,
        )

    async def _external_then_local(
        self,
        request: ModelRequest,
    ) -> GatewayResponse:
        try:
            response = await self._external.generate(request)
            return GatewayResponse(
                text=response.text,
                model=response.model,
                provider="external",
                route_reason=("public_or_allowed_internal"),
                external_sent=True,
            )
        except Exception:
            response = await self._local.generate(request)
            return GatewayResponse(
                text=response.text,
                model=response.model,
                provider="ollama",
                route_reason=("external_failed_fallback_local"),
                external_sent=False,
            )

    async def _local_only(
        self,
        request: ModelRequest,
        sensitivity: Sensitivity,
    ) -> GatewayResponse:
        try:
            response = await self._local.generate(request)
        except Exception as exc:
            raise SensitiveModelUnavailable("本地模型不可用，受保护请求已拒绝") from exc

        return GatewayResponse(
            text=response.text,
            model=response.model,
            provider="ollama",
            route_reason=(f"{sensitivity.value}_requires_local"),
            external_sent=False,
        )
