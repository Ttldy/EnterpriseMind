from typing import Any

import httpx

from app.model_gateway.contracts import (
    ModelRequest,
    ModelResponse,
)


class OllamaProvider:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = 120.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": request.system_prompt,
                },
                {
                    "role": "user",
                    "content": request.user_message,
                },
            ],
            "stream": False,
            "options": {
                "temperature": 0.1,
            },
        }

        timeout = httpx.Timeout(self._timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        message = data.get("message")
        if not isinstance(message, dict):
            raise RuntimeError("Ollama response has no message")

        content = message.get("content")
        if not isinstance(content, str):
            raise RuntimeError("Ollama response has no text content")

        return ModelResponse(
            text=content.strip(),
            model=str(data.get("model", self._model)),
        )
