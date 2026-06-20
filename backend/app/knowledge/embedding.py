import hashlib
import math
from typing import Protocol


class EmbeddingProvider(Protocol):
    dimensions: int

    async def embed(self, text: str) -> list[float]: ...


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
