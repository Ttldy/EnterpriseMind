from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.security import (
    InvalidAccessTokenError,
    decode_access_token,
)
from app.auth.service import get_user_by_id
from app.knowledge.access import (
    AccessContext,
    build_access_context,
)
from app.shared.database import get_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效或已过期的访问令牌",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        user_id = decode_access_token(token)
    except InvalidAccessTokenError as exc:
        raise credentials_error from exc

    user = await get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return user


async def get_access_context(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AccessContext:
    return await build_access_context(
        session,
        user,
    )


def require_role(
    required_role: str,
) -> Callable[..., Awaitable[User]]:
    async def dependency(
        user: User = Depends(get_current_user),
    ) -> User:
        roles = {role.name for role in user.roles}
        if required_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足",
            )
        return user

    return dependency
