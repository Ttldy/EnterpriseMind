from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class ReadOnlyExecutor:
    def __init__(
        self,
        engine: AsyncEngine,
        timeout_seconds: int = 5,
    ) -> None:
        self._engine = engine
        self._session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self._timeout_milliseconds = timeout_seconds * 1000

    async def execute(
        self,
        sql: str,
    ) -> list[dict[str, object]]:
        async with self._session() as session:
            await session.execute(text("SET TRANSACTION READ ONLY"))
            await session.execute(
                text("SET LOCAL statement_timeout " f"= {self._timeout_milliseconds}")
            )
            result = await session.execute(text(sql))
            return [dict(row._mapping) for row in result.fetchall()]

    @asynccontextmanager
    async def _session(
        self,
    ) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as session:
            async with session.begin():
                yield session


def create_readonly_engine(
    database_url: str,
) -> AsyncEngine:
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
    )
