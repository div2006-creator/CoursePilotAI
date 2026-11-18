"""Pydantic schemas for authentication requests, responses, and JWT payloads."""
from __future__ import annotations

from datetime import datetime
from typing import Generic, Optional, TypeVar
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

T = TypeVar("T")

MAX_BCRYPT_PASSWORD_BYTES = 72


def normalize_email_value(value: str) -> str:
    """Trim whitespace and normalize email addresses to lowercase."""
    return value.strip().lower()


class APIResponse(BaseModel, Generic[T]):
    """Standardized API success response wrapper."""

    success: bool = Field(default=True, description="Indicates request outcome")
    data: T = Field(description="Primary response payload")
    message: str = Field(description="Human-readable operation status message")


class ErrorResponse(BaseModel):
    """Standardized API error response structure."""

    success: bool = Field(default=False)
    data: Optional[dict] = Field(default=None)
    message: str = Field(description="Human-readable error summary")
    detail: Optional[object] = Field(default=None, description="Additional error details")


class RegisterRequest(BaseModel):
    """Payload for registering a new learner account."""

    name: str = Field(..., min_length=2, max_length=120, description="Full display name")
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="Account password (at least 8 characters)",
    )

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("name", mode="after")
    @classmethod
    def validate_name_non_blank(cls, value: str) -> str:
        if len(value) < 2:
            raise ValueError("Name must be at least 2 characters long")
        return value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_email_value(value)
        return value

    @field_validator("password", mode="after")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
            raise ValueError(
                f"Password must not exceed {MAX_BCRYPT_PASSWORD_BYTES} bytes"
            )
        return value


class LoginRequest(BaseModel):
    """Credentials payload for email/password login."""

    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., min_length=1, max_length=128, description="Account password")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_email_value(value)
        return value


class UserResponse(BaseModel):
    """Public representation of a learner account (never includes password fields)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: EmailStr
    created_at: datetime


class TokenResponse(BaseModel):
    """JWT bearer token response payload."""

    access_token: str = Field(..., description="Signed JWT access token")
    token_type: str = Field(default="bearer", description="Authentication token scheme")


class TokenPayload(BaseModel):
    """Decoded JWT access token claims."""

    sub: str = Field(..., description="Subject identifier (user UUID)")
    exp: int = Field(..., description="Expiration timestamp (UTC Unix seconds)")


class RegisterResponse(APIResponse[UserResponse]):
    """Standardized response for POST /api/v1/auth/register."""


class LoginResponse(APIResponse[TokenResponse]):
    """Standardized response for POST /api/v1/auth/login."""


class CurrentUserResponse(APIResponse[UserResponse]):
    """Standardized response for GET /api/v1/auth/me."""

