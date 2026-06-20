from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.shared.config import get_settings

password_hash = PasswordHash.recommended()


class InvalidAccessTokenError(ValueError):
    pass


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    encoded_password: str,
) -> bool:
    return password_hash.verify(
        plain_password,
        encoded_password,
    )


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "exp": expires_at,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> int:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        subject = payload.get("sub")
        if subject is None:
            raise InvalidAccessTokenError("token has no subject")
        return int(subject)
    except (
        InvalidTokenError,
        TypeError,
        ValueError,
    ) as exc:
        raise InvalidAccessTokenError("invalid access token") from exc
