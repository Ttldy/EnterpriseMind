import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import app.models  # noqa: F401
from app.auth.models import Department, Role, User
from app.auth.security import hash_password
from app.shared.database import Base


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    database_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_session(session_factory):
    async with session_factory() as session:
        it_department = Department(name="IT")
        finance_department = Department(name="FINANCE")

        employee = Role(name="employee")
        it_staff = Role(name="it_staff")
        finance_staff = Role(name="finance_staff")

        it_user = User(
            username="it01",
            password_hash=hash_password("ItPassw0rd!"),
            department=it_department,
            roles=[employee, it_staff],
        )
        finance_user = User(
            username="finance01",
            password_hash=hash_password("FinancePassw0rd!"),
            department=finance_department,
            roles=[employee, finance_staff],
        )

        session.add_all([it_user, finance_user])
        await session.commit()

    return session_factory
