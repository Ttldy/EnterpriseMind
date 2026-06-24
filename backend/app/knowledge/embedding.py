import hashlib
import math
from typing import Protocol

import httpx


class EmbeddingProvider(Protocol):
    dimensions: int

    async def embed(self, text: str) -> list[float]: ...


class EmbeddingError(RuntimeError):
    pass


class OllamaEmbeddingProvider:
    def __init__(
        self,
        base_url: str,
        model: str,
        dimensions: int,
        timeout_seconds: float,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self.dimensions = dimensions
        self._timeout_seconds = timeout_seconds

    async def embed(self, text: str) -> list[float]:
        normalized = text.strip()
        if not normalized:
            return [0.0] * self.dimensions

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
            ) as client:
                response = await client.post(
                    f"{self._base_url}/api/embed",
                    json={
                        "model": self._model,
                        "input": normalized,
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            raise EmbeddingError("Ollama embedding request failed") from exc

        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list) or not embeddings:
            raise EmbeddingError("Ollama embedding response has no embeddings")

        vector = embeddings[0]
        if not isinstance(vector, list):
            raise EmbeddingError("Ollama embedding vector is invalid")

        values = [float(item) for item in vector]
        if len(values) != self.dimensions:
            raise EmbeddingError(
                "Ollama embedding dimension mismatch: "
                f"expected {self.dimensions}, got {len(values)}"
            )
        return values


class HashEmbeddingProvider:
    def __init__(
        self,
        dimensions: int = 384,
    ) -> None:
        self.dimensions = dimensions

    async def embed(self, text: str) -> list[float]:
        normalized = text.lower().strip()
        vector = [0.0] * self.dimensions

        tokens: set[str] = set()
        for size in (1, 2, 3):
            for index in range(max(0, len(normalized) - size + 1)):
                tokens.add(normalized[index : index + size])

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            position = (
                int.from_bytes(
                    digest[:4],
                    "big",
                )
                % self.dimensions
            )
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[position] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]
