from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import require_role
from app.auth.models import Department, Role, User
from app.auth.security import hash_password
from app.shared.database import get_session

router = APIRouter(
    prefix="/admin/users",
    tags=["admin-users"],
)


class UserCreate(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=64,
    )
    password: str = Field(
        min_length=10,
        max_length=128,
    )
    department_id: int
    role_ids: list[int] = Field(min_length=1)


class UserUpdate(BaseModel):
    department_id: int | None = None
    role_ids: list[int] | None = None
    is_active: bool | None = None


def serialize_user(user: User) -> dict[str, object]:
    return {
        "id": user.id,
        "username": user.username,
        "department": {
            "id": user.department.id,
            "name": user.department.name,
        },
        "roles": [
            {"id": role.id, "name": role.name}
            for role in sorted(
                user.roles,
                key=lambda item: item.name,
            )
        ],
        "is_active": user.is_active,
    }


async def load_user(
    session: AsyncSession,
    user_id: int,
) -> User | None:
    user: User | None = await session.scalar(
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.department),
            selectinload(User.roles),
        )
    )
    return user


async def load_department_and_roles(
    session: AsyncSession,
    department_id: int,
    role_ids: list[int],
) -> tuple[Department, list[Role]]:
    department = await session.get(
        Department,
        department_id,
    )
    roles = list(
        (
            await session.scalars(
                select(Role).where(
                    Role.id.in_(set(role_ids))
                )
            )
        ).all()
    )
    if department is None:
        raise HTTPException(
            status_code=422,
            detail="department does not exist",
        )
    if len(roles) != len(set(role_ids)):
        raise HTTPException(
            status_code=422,
            detail="one or more roles do not exist",
        )
    return department, roles


@router.get("/options")
async def list_options(
    _: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    departments = list(
        (
            await session.scalars(
                select(Department).order_by(
                    Department.name
                )
            )
        ).all()
    )
    roles = list(
        (
            await session.scalars(
                select(Role).order_by(Role.name)
            )
        ).all()
    )
    return {
        "departments": [
            {"id": item.id, "name": item.name}
            for item in departments
        ],
        "roles": [
            {"id": item.id, "name": item.name}
            for item in roles
        ],
    }


@router.get("")
async def list_users(
    _: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, object]]:
    users = (
        await session.scalars(
            select(User)
            .options(
                selectinload(User.department),
                selectinload(User.roles),
            )
            .order_by(User.id)
        )
    ).all()
    return [serialize_user(user) for user in users]


@router.post("", status_code=201)
async def create_user(
    body: UserCreate,
    _: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    existing = await session.scalar(
        select(User).where(
            User.username == body.username
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="username already exists",
        )

    department, roles = (
        await load_department_and_roles(
            session,
            body.department_id,
            body.role_ids,
        )
    )
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        department=department,
        roles=roles,
    )
    session.add(user)
    await session.commit()
    loaded = await load_user(session, user.id)
    assert loaded is not None
    return serialize_user(loaded)


@router.patch("/{user_id}")
async def update_user(
    user_id: int,
    body: UserUpdate,
    current_admin: User = Depends(
        require_role("admin")
    ),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    user = await load_user(session, user_id)
    if user is None:
        raise HTTPException(
            status_code=404,
            detail="user not found",
        )
    if (
        current_admin.id == user.id
        and body.is_active is False
    ):
        raise HTTPException(
            status_code=422,
            detail="cannot disable current admin",
        )

    if body.department_id is not None:
        department = await session.get(
            Department,
            body.department_id,
        )
        if department is None:
            raise HTTPException(
                status_code=422,
                detail="department does not exist",
            )
        user.department = department

    if body.role_ids is not None:
        _, roles = await load_department_and_roles(
            session,
            user.department_id,
            body.role_ids,
        )
        user.roles = roles

    if body.is_active is not None:
        user.is_active = body.is_active

    await session.commit()
    loaded = await load_user(session, user.id)
    assert loaded is not None
    return serialize_user(loaded)
