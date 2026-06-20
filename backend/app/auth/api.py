from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.auth.schemas import (
    CurrentUserResponse,
    TokenResponse,
)
from app.auth.security import create_access_token
from app.auth.service import authenticate_user
from app.shared.database import get_session

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    form: Annotated[
        OAuth2PasswordRequestForm,
        Depends(),
    ],
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    user = await authenticate_user(
        session,
        form.username,
        form.password,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(access_token=create_access_token(user.id))


@router.get(
    "/me",
    response_model=CurrentUserResponse,
)
async def me(
    user: User = Depends(get_current_user),
) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=user.id,
        username=user.username,
        department=user.department.name,
        roles=sorted(role.name for role in user.roles),
    )
