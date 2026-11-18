"""Authentication domain service layer."""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import RegisterRequest, normalize_email_value

logger = logging.getLogger(__name__)


class AuthServiceError(Exception):
    """Base application error for authentication operations."""


class EmailAlreadyRegisteredError(AuthServiceError):
    """Raised when attempting to register with an email that already exists."""


class InvalidCredentialsError(AuthServiceError):
    """Raised when login credentials do not match any account."""


class AuthServiceDatabaseError(AuthServiceError):
    """Raised when an unexpected database failure occurs during auth operations."""


def get_user_by_email(db: Session, email: str) -> User | None:
    """Retrieve a user by normalized lowercase email address."""
    normalized = normalize_email_value(email)
    stmt = select(User).where(User.email == normalized)
    return db.scalar(stmt)


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    """Retrieve a user by UUID primary key."""
    stmt = select(User).where(User.id == user_id)
    return db.scalar(stmt)


def register_user(db: Session, payload: RegisterRequest) -> User:
    """Create a new learner account with normalized email and bcrypt password hash."""
    normalized_email = normalize_email_value(str(payload.email))

    existing_user = get_user_by_email(db, normalized_email)
    if existing_user is not None:
        raise EmailAlreadyRegisteredError(
            "An account with this email address already exists"
        )

    user = User(
        name=payload.name.strip(),
        email=normalized_email,
        password_hash=hash_password(payload.password),
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError as exc:
        db.rollback()
        logger.warning(
            "Duplicate registration race condition for email %s: %s",
            normalized_email,
            exc,
        )
        raise EmailAlreadyRegisteredError(
            "An account with this email address already exists"
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Database error while registering user: %s", exc)
        raise AuthServiceDatabaseError("Failed to create user account") from exc


def authenticate_user(db: Session, email: str, password: str) -> User:
    """Validate email and password credentials and return the matching User."""
    normalized_email = normalize_email_value(email)
    user = get_user_by_email(db, normalized_email)

    # Always return the same generic error for unknown email or wrong password
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Invalid email or password")

    return user

