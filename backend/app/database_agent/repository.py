from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database_agent.models import Dataset
from app.knowledge.access import AccessContext


@dataclass(frozen=True)
class DatasetPolicy:
    id: int
    name: str
    view_name: str
    description: str
    schema_text: str
    sensitivity: str
    allowed_columns: frozenset[str]
    keywords: tuple[str, ...]


class DatasetLoader(Protocol):
    async def list_authorized(
        self,
        access: AccessContext,
    ) -> list[DatasetPolicy]: ...


class SqlAlchemyDatasetRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def list_authorized(
        self,
        access: AccessContext,
    ) -> list[DatasetPolicy]:
        if not access.dataset_ids:
            return []

        statement = (
            select(Dataset)
            .where(
                Dataset.id.in_(access.dataset_ids),
                Dataset.is_active.is_(True),
            )
            .order_by(Dataset.id)
        )
        datasets = (await self._session.scalars(statement)).all()

        return [
            DatasetPolicy(
                id=item.id,
                name=item.name,
                view_name=item.view_name,
                description=item.description,
                schema_text=item.schema_text,
                sensitivity=item.sensitivity,
                allowed_columns=frozenset(item.allowed_columns),
                keywords=tuple(item.keywords),
            )
            for item in datasets
        ]
