"""Authenticated Course Management API routes."""
from __future__ import annotations

from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.course import (
    CourseCreate,
    CourseListData,
    CourseListResponse,
    CourseResponse,
    CourseSingleResponse,
    CourseUpdate,
)
from app.services.course_service import (
    CourseDatabaseError,
    CourseNotFoundError,
    CourseValidationError,
    create_course,
    delete_course,
    get_course_by_id,
    get_user_courses,
    update_course,
)

router = APIRouter()


@router.post(
    "",
    response_model=CourseSingleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new course",
)
def create_course_endpoint(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CourseSingleResponse:
    try:
        course = create_course(db, current_user.id, payload)
    except CourseDatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return CourseSingleResponse(
        success=True,
        data=CourseResponse.model_validate(course),
        message="Course created successfully",
    )


@router.get(
    "",
    response_model=CourseListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all courses belonging to the authenticated user",
)
def list_courses_endpoint(
    search: Optional[str] = Query(
        default=None,
        max_length=100,
        description="Optional case-insensitive filter on course title or description",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CourseListResponse:
    courses = get_user_courses(db, current_user.id, search=search)
    serialized = [CourseResponse.model_validate(c) for c in courses]
    return CourseListResponse(
        success=True,
        data=CourseListData(courses=serialized, total=len(serialized)),
        message="Courses retrieved successfully",
    )


@router.get(
    "/{course_id}",
    response_model=CourseSingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get details for a specific course",
)
def get_course_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CourseSingleResponse:
    try:
        course = get_course_by_id(db, course_id, current_user.id)
    except CourseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return CourseSingleResponse(
        success=True,
        data=CourseResponse.model_validate(course),
        message="Course retrieved successfully",
    )


@router.patch(
    "/{course_id}",
    response_model=CourseSingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing course",
)
def update_course_endpoint(
    course_id: uuid.UUID,
    payload: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CourseSingleResponse:
    try:
        course = update_course(db, course_id, current_user.id, payload)
    except CourseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except CourseValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except CourseDatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return CourseSingleResponse(
        success=True,
        data=CourseResponse.model_validate(course),
        message="Course updated successfully",
    )


@router.delete(
    "/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a course",
)
def delete_course_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    try:
        delete_course(db, course_id, current_user.id)
    except CourseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except CourseDatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
