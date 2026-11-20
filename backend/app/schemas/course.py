"""Pydantic schemas for course creation, updates, and API responses."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.schemas.auth import APIResponse

MIN_TITLE_LENGTH = 2
MAX_TITLE_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 2000
MIN_DAILY_MINUTES = 15
MAX_DAILY_MINUTES = 720

ExamStatus = Literal["no_exam_date", "passed", "today", "urgent", "upcoming"]


class CourseCreate(BaseModel):
    """Request payload for creating a new course."""

    title: str = Field(
        ...,
        min_length=MIN_TITLE_LENGTH,
        max_length=MAX_TITLE_LENGTH,
        description="Course title (2–100 characters)",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=MAX_DESCRIPTION_LENGTH,
        description="Optional short course description",
    )
    exam_date: Optional[date] = Field(
        default=None,
        description="Target exam date (YYYY-MM-DD). Past dates are permitted and flagged.",
    )
    daily_minutes: int = Field(
        default=60,
        ge=MIN_DAILY_MINUTES,
        le=MAX_DAILY_MINUTES,
        description="Daily available study time in minutes (15–720)",
    )

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("title", mode="after")
    @classmethod
    def validate_title_length(cls, value: str) -> str:
        if len(value) < MIN_TITLE_LENGTH:
            raise ValueError(f"Title must be at least {MIN_TITLE_LENGTH} characters long")
        return value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned if cleaned else None
        return value


class CourseUpdate(BaseModel):
    """Partial update payload for modifying an existing course."""

    title: Optional[str] = Field(
        default=None,
        min_length=MIN_TITLE_LENGTH,
        max_length=MAX_TITLE_LENGTH,
        description="Updated course title (2–100 characters)",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=MAX_DESCRIPTION_LENGTH,
        description="Updated course description (pass null or empty string to clear)",
    )
    exam_date: Optional[date] = Field(
        default=None,
        description="Updated exam date (YYYY-MM-DD, pass null to clear)",
    )
    daily_minutes: Optional[int] = Field(
        default=None,
        ge=MIN_DAILY_MINUTES,
        le=MAX_DAILY_MINUTES,
        description="Updated daily study minutes (15–720)",
    )

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("title", mode="after")
    @classmethod
    def validate_title_non_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and len(value) < MIN_TITLE_LENGTH:
            raise ValueError(f"Title must be at least {MIN_TITLE_LENGTH} characters long")
        return value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned if cleaned else None
        return value


class CourseResponse(BaseModel):
    """Serialized representation of a course with computed exam countdown metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: Optional[str] = None
    exam_date: Optional[date] = None
    daily_minutes: int
    created_at: datetime

    @computed_field
    @property
    def days_remaining(self) -> Optional[int]:
        """Signed number of days until the exam date (negative if exam has passed)."""
        if self.exam_date is None:
            return None
        return (self.exam_date - date.today()).days

    @computed_field
    @property
    def is_exam_passed(self) -> bool:
        """True when an exam date is set and lies strictly before today."""
        return self.exam_date is not None and self.exam_date < date.today()

    @computed_field
    @property
    def exam_status(self) -> ExamStatus:
        """Human-friendly status bucket derived from exam_date."""
        if self.exam_date is None:
            return "no_exam_date"
        remaining = (self.exam_date - date.today()).days
        if remaining < 0:
            return "passed"
        if remaining == 0:
            return "today"
        if remaining <= 7:
            return "urgent"
        return "upcoming"


class CourseListData(BaseModel):
    """Container for a list of courses and total count."""

    courses: list[CourseResponse]
    total: int


class CourseSingleResponse(APIResponse[CourseResponse]):
    """Standardized response for single-course endpoints."""


class CourseListResponse(APIResponse[CourseListData]):
    """Standardized response for GET /api/v1/courses."""
