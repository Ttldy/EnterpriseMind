from typing import Any

import httpx

from app.model_gateway.contracts import ModelRequest, ModelResponse


class ExternalModelProvider:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def generate(self, request: ModelRequest) -> ModelResponse:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
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
            "temperature": 0.1,
        }

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        text = str(data["choices"][0]["message"]["content"])
        return ModelResponse(
            text=text,
            model=self._model,
        )