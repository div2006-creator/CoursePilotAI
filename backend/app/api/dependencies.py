"""FastAPI dependency injection providers for database sessions and authentication."""
from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import ExpiredTokenError, InvalidTokenError, decode_access_token
from app.models.user import User
from app.schemas.auth import TokenPayload
from app.services.auth_service import get_user_by_id

# HTTP Bearer scheme integrates cleanly with FastAPI OpenAPI / Swagger Authorize modal
bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",
    description="Enter your JWT access token (obtained from POST /api/v1/auth/login).",
    auto_error=False,
)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve and return the currently authenticated User from a JWT Bearer token."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Authentication credentials were not provided")

    token = credentials.credentials.strip()
    if not token:
        raise _unauthorized("Authentication credentials were not provided")

    try:
        raw_payload = decode_access_token(token)
        token_payload = TokenPayload.model_validate(raw_payload)
    except ExpiredTokenError as exc:
        raise _unauthorized("Access token has expired") from exc
    except (InvalidTokenError, ValidationError) as exc:
        raise _unauthorized("Invalid authentication token") from exc

    try:
        user_id = uuid.UUID(token_payload.sub)
    except ValueError as exc:
        raise _unauthorized("Invalid authentication token subject") from exc

    user = get_user_by_id(db, user_id)
    if user is None:
        raise _unauthorized("Authenticated user no longer exists")

    return user


def ensure_resource_owner(current_user: User, owner_id: uuid.UUID) -> None:
    """Enforce ownership checks with HTTP 403 Forbidden for authenticated users."""
    if current_user.id != owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource",
        )


__all__ = ["get_db", "bearer_scheme", "get_current_user", "ensure_resource_owner"]
