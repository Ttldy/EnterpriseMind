from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ModelRequest:
    system_prompt: str
    user_message: str


@dataclass(frozen=True)
class ModelResponse:
    text: str
    model: str


@dataclass(frozen=True)
class GatewayResponse:
    text: str
    model: str
    provider: str
    route_reason: str
    external_sent: bool


class ModelProvider(Protocol):
    async def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse: ...
