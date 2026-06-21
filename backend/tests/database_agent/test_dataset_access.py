import pytest
from sqlalchemy import select

from app.auth.models import User
from app.database_agent.models import (
    Dataset,
    DatasetPermission,
)
from app.knowledge.access import (
    build_access_context,
)


@pytest.mark.asyncio
async def test_finance_role_gets_expense_dataset(
    seeded_session,
) -> None:
    async with seeded_session() as session:
        dataset = Dataset(
            name="expense_summary",
            view_name="expense_summary_view",
            description="报销",
            schema_text=("expense_summary_view(" "department text)"),
            sensitivity="sensitive",
            allowed_columns=["department"],
            keywords=["报销统计"],
        )
        dataset.permissions.append(
            DatasetPermission(
                subject_type="ROLE",
                subject_value="finance_staff",
            )
        )
        session.add(dataset)
        await session.commit()

        user = await session.scalar(select(User).where(User.username == "it01"))
        assert user is not None

        access = await build_access_context(
            session,
            user,
        )

        assert dataset.id not in access.dataset_ids


@pytest.mark.asyncio
async def test_finance_role_gets_dataset(
    seeded_session,
) -> None:
    async with seeded_session() as session:
        dataset = Dataset(
            name="expense_summary",
            view_name="expense_summary_view",
            description="报销",
            schema_text=("expense_summary_view(" "department text)"),
            sensitivity="sensitive",
            allowed_columns=["department"],
            keywords=["报销统计"],
        )
        dataset.permissions.append(
            DatasetPermission(
                subject_type="ROLE",
                subject_value="finance_staff",
            )
        )
        session.add(dataset)
        await session.commit()

        user = await session.scalar(select(User).where(User.username == "finance01"))
        assert user is not None

        access = await build_access_context(
            session,
            user,
        )

        assert dataset.id in access.dataset_ids
