from typing import Protocol

from app.evaluation.prompt_service import PromptService


class PromptResolver(Protocol):
    async def resolve(
        self,
        prompt_key: str,
        fallback: str,
    ) -> str:
        ...


class DatabasePromptResolver:
    def __init__(
        self,
        service: PromptService,
    ) -> None:
        self._service = service

    async def resolve(
        self,
        prompt_key: str,
        fallback: str,
    ) -> str:
        return await self._service.resolve(
            prompt_key,
            fallback,
        )