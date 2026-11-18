"""Password hashing and JWT authentication utilities."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

import bcrypt
from jose import ExpiredSignatureError, JWTError, jwt

from app.config import settings

BCRYPT_ROUNDS = 12
MAX_BCRYPT_PASSWORD_BYTES = 72


class TokenError(Exception):
    """Base exception for JWT decoding and validation failures."""


class ExpiredTokenError(TokenError):
    """Raised when a JWT access token has expired."""


class InvalidTokenError(TokenError):
    """Raised when a JWT access token is malformed, unsigned, or invalid."""


def hash_password(password: str) -> str:
    """Hash a plain-text password with bcrypt and a unique per-password salt."""
    if not password:
        raise ValueError("Password cannot be empty")
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > MAX_BCRYPT_PASSWORD_BYTES:
        raise ValueError(
            f"Password must not exceed {MAX_BCRYPT_PASSWORD_BYTES} UTF-8 bytes"
        )
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a stored bcrypt hash in constant time."""
    if not plain_password or not hashed_password:
        return False
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > MAX_BCRYPT_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str | uuid.UUID,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT access token for the given user subject."""
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT access token, enforcing signature and expiration."""
    if not token or not token.strip():
        raise InvalidTokenError("Token is missing")

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require_sub": True, "require_exp": True},
        )
    except ExpiredSignatureError as exc:
        raise ExpiredTokenError("Access token has expired") from exc
    except JWTError as exc:
        raise InvalidTokenError("Could not validate access token") from exc

    if not payload.get("sub") or not isinstance(payload.get("sub"), str):
        raise InvalidTokenError("Token payload is missing a valid subject")

    return payload

