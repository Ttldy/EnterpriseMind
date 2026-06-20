import json
from collections.abc import Awaitable
from dataclasses import asdict, dataclass
from typing import Protocol, cast

from redis.asyncio import Redis


@dataclass(frozen=True)
class CachedMessage:
    role: str
    content: str


class RecentMessageCache(Protocol):
    async def append(
        self,
        conversation_id: int,
        message: CachedMessage,
        limit: int = 8,
    ) -> None: ...

    async def get(
        self,
        conversation_id: int,
    ) -> list[CachedMessage]: ...

    async def delete(
        self,
        conversation_id: int,
    ) -> None: ...


class RedisRecentMessageCache:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    @staticmethod
    def _key(conversation_id: int) -> str:
        return f"conversation:{conversation_id}:recent"

    async def append(
        self,
        conversation_id: int,
        message: CachedMessage,
        limit: int = 8,
    ) -> None:
        key = self._key(conversation_id)
        await cast(
            Awaitable[int],
            self._redis.rpush(
                key,
                json.dumps(
                    asdict(message),
                    ensure_ascii=False,
                ),
            ),
        )
        await cast(
            Awaitable[str],
            self._redis.ltrim(key, -limit, -1),
        )
        await cast(
            Awaitable[int],
            self._redis.expire(key, 86400),
        )

    async def get(
        self,
        conversation_id: int,
    ) -> list[CachedMessage]:
        values = await cast(
            Awaitable[list[str]],
            self._redis.lrange(
                self._key(conversation_id),
                0,
                -1,
            ),
        )
        return [CachedMessage(**json.loads(value)) for value in values]

    async def delete(
        self,
        conversation_id: int,
    ) -> None:
        await self._redis.delete(self._key(conversation_id))
