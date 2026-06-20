import asyncio

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth.models import Department, Role, User
from app.auth.security import hash_password
from app.knowledge.models import (
    KnowledgeBase,
    KnowledgePermission,
)
from app.shared.database import SessionFactory


async def get_or_create_department(
    session,
    name: str,
) -> Department:
    department = await session.scalar(select(Department).where(Department.name == name))
    if department is None:
        department = Department(name=name)
        session.add(department)
        await session.flush()
    return department


async def get_or_create_role(
    session,
    name: str,
) -> Role:
    role = await session.scalar(select(Role).where(Role.name == name))
    if role is None:
        role = Role(name=name)
        session.add(role)
        await session.flush()
    return role


async def create_user_if_missing(
    session,
    username: str,
    password: str,
    department: Department,
    roles: list[Role],
) -> None:
    existing = await session.scalar(
        select(User).where(User.username == username).options(selectinload(User.roles))
    )
    if existing is not None:
        return

    session.add(
        User(
            username=username,
            password_hash=hash_password(password),
            department=department,
            roles=roles,
        )
    )


async def main() -> None:
    async with SessionFactory() as session:
        general = await get_or_create_department(
            session,
            "GENERAL",
        )
        it_department = await get_or_create_department(
            session,
            "IT",
        )
        hr_department = await get_or_create_department(
            session,
            "HR",
        )
        finance_department = await get_or_create_department(
            session,
            "FINANCE",
        )

        employee = await get_or_create_role(
            session,
            "employee",
        )
        it_staff = await get_or_create_role(
            session,
            "it_staff",
        )
        hr_staff = await get_or_create_role(
            session,
            "hr_staff",
        )
        finance_staff = await get_or_create_role(
            session,
            "finance_staff",
        )
        admin = await get_or_create_role(
            session,
            "admin",
        )

        await create_user_if_missing(
            session,
            "employee01",
            "EmployeePassw0rd!",
            general,
            [employee],
        )
        await create_user_if_missing(
            session,
            "it01",
            "ItPassw0rd!",
            it_department,
            [employee, it_staff],
        )
        await create_user_if_missing(
            session,
            "hr01",
            "HrPassw0rd!",
            hr_department,
            [employee, hr_staff],
        )
        await create_user_if_missing(
            session,
            "finance01",
            "FinancePassw0rd!",
            finance_department,
            [employee, finance_staff],
        )
        await create_user_if_missing(
            session,
            "admin",
            "AdminPassw0rd!",
            general,
            [employee, admin],
        )

        public_kb = await session.scalar(
            select(KnowledgeBase).where(KnowledgeBase.name == "公共知识库")
        )
        if public_kb is None:
            public_kb = KnowledgeBase(
                name="公共知识库",
                domain="general",
                sensitivity="public",
                is_public=True,
            )
            session.add(public_kb)

        it_kb = await session.scalar(
            select(KnowledgeBase).where(KnowledgeBase.name == "IT 内部知识库")
        )
        if it_kb is None:
            it_kb = KnowledgeBase(
                name="IT 内部知识库",
                domain="it",
                sensitivity="internal",
                is_public=False,
            )
            it_kb.permissions.append(
                KnowledgePermission(
                    subject_type="ROLE",
                    subject_value="it_staff",
                )
            )
            it_kb.permissions.append(
                KnowledgePermission(
                    subject_type="ROLE",
                    subject_value="admin",
                )
            )
            session.add(it_kb)

        await session.commit()

    print("stage1 demo data seeded")


if __name__ == "__main__":
    asyncio.run(main())
