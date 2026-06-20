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


class ModelProvider(Protocol):
    async def generate(self, request: ModelRequest) -> ModelResponse: ...
