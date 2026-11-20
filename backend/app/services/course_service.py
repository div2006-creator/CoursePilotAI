"""Course management domain service with strict user-level ownership isolation."""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.course import Course
from app.schemas.course import CourseCreate, CourseUpdate

logger = logging.getLogger(__name__)


class CourseServiceError(Exception):
    """Base application error for course operations."""


class CourseNotFoundError(CourseServiceError):
    """Raised when a course does not exist or is not owned by the requesting user."""


class CourseValidationError(CourseServiceError):
    """Raised when an update payload attempts to nullify a required field."""


class CourseDatabaseError(CourseServiceError):
    """Raised when an unexpected database failure occurs during course persistence."""


def create_course(
    db: Session,
    user_id: uuid.UUID,
    payload: CourseCreate,
) -> Course:
    """Create and persist a new course owned by `user_id`."""
    course = Course(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        exam_date=payload.exam_date,
        daily_minutes=payload.daily_minutes,
    )

    try:
        db.add(course)
        db.commit()
        db.refresh(course)
        return course
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Database error while creating course for user %s: %s", user_id, exc)
        raise CourseDatabaseError("Failed to create course") from exc


def get_user_courses(
    db: Session,
    user_id: uuid.UUID,
    *,
    search: str | None = None,
) -> list[Course]:
    """Return all courses owned by `user_id`, ordered newest first."""
    stmt = select(Course).where(Course.user_id == user_id)

    if search and search.strip():
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Course.title.ilike(pattern),
                Course.description.ilike(pattern),
            )
        )

    stmt = stmt.order_by(Course.created_at.desc())
    return list(db.scalars(stmt).all())


def get_course_by_id(
    db: Session,
    course_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Course:
    """Retrieve a single course if and only if it belongs to `user_id`."""
    stmt = select(Course).where(
        Course.id == course_id,
        Course.user_id == user_id,
    )
    course = db.scalar(stmt)
    if course is None:
        # Deliberately return a uniform not-found error to avoid leaking other users' IDs
        raise CourseNotFoundError("Course not found")
    return course


def update_course(
    db: Session,
    course_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: CourseUpdate,
) -> Course:
    """Apply partial updates to a course owned by `user_id`."""
    course = get_course_by_id(db, course_id, user_id)
    provided_fields = payload.model_fields_set

    if "title" in provided_fields:
        if payload.title is None:
            raise CourseValidationError("Title cannot be null")
        course.title = payload.title

    if "description" in provided_fields:
        course.description = payload.description

    if "exam_date" in provided_fields:
        course.exam_date = payload.exam_date

    if "daily_minutes" in provided_fields:
        if payload.daily_minutes is None:
            raise CourseValidationError("Daily study minutes cannot be null")
        course.daily_minutes = payload.daily_minutes

    try:
        db.add(course)
        db.commit()
        db.refresh(course)
        return course
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Database error while updating course %s: %s", course_id, exc)
        raise CourseDatabaseError("Failed to update course") from exc


def delete_course(
    db: Session,
    course_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Delete a course owned by `user_id`."""
    course = get_course_by_id(db, course_id, user_id)

    try:
        db.delete(course)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Database error while deleting course %s: %s", course_id, exc)
        raise CourseDatabaseError("Failed to delete course") from exc
