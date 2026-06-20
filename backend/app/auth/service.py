from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.models import User
from app.auth.security import verify_password


async def get_user_by_username(
    session: AsyncSession,
    username: str,
) -> User | None:
    statement = (
        select(User)
        .where(User.username == username)
        .options(
            selectinload(User.department),
            selectinload(User.roles),
        )
    )
    return cast(
        User | None,
        await session.scalar(statement),
    )


async def get_user_by_id(
    session: AsyncSession,
    user_id: int,
) -> User | None:
    statement = (
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.department),
            selectinload(User.roles),
        )
    )
    return cast(
        User | None,
        await session.scalar(statement),
    )


async def authenticate_user(
    session: AsyncSession,
    username: str,
    password: str,
) -> User | None:
    user = await get_user_by_username(
        session,
        username,
    )
    if user is None or not user.is_active:
        return None
    if not verify_password(
        password,
        user.password_hash,
    ):
        return None
    return user
