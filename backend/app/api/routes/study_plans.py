"""API routes for Adaptive Learning Planner."""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.study_plan import (
    PlanItemResponseEnvelope,
    PlanItemUpdatePayload,
    StudyPlanGeneratePayload,
    StudyPlanHistoryResponse,
    StudyPlanResponse,
)
from app.services.learning_planner_service import (
    CourseEmptyError,
    CourseNotFoundError,
    PlanNotFoundError,
    PlannerError,
    generate_learning_plan,
    get_active_study_plan,
    get_study_plan_by_id,
    get_study_plan_history,
    rebalance_learning_plan,
    update_plan_item_status,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/courses/{course_id}/study-plan/generate",
    response_model=StudyPlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate or regenerate an adaptive learning plan for a course",
)
def generate_study_plan_endpoint(
    course_id: uuid.UUID,
    payload: Optional[StudyPlanGeneratePayload] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudyPlanResponse:
    """Generate a personalized, prerequisite-respecting study roadmap."""
    exam_date = payload.exam_date if payload else None
    daily_minutes = payload.daily_minutes if payload else None
    force_regenerate = payload.force_regenerate if payload else False

    try:
        plan_data = generate_learning_plan(
            db=db,
            user_id=current_user.id,
            course_id=course_id,
            exam_date=exam_date,
            daily_minutes=daily_minutes,
            force_regenerate=force_regenerate,
        )
        return StudyPlanResponse(
            success=True,
            data=plan_data,
            message="Adaptive learning plan generated successfully",
        )
    except CourseNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CourseEmptyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PlannerError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error generating study plan for course %s", course_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate study plan: {str(e)}",
        )


@router.get(
    "/courses/{course_id}/study-plan",
    response_model=StudyPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Get active study plan for a course",
)
@router.get(
    "/courses/{course_id}/study-plan/active",
    response_model=StudyPlanResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_active_study_plan_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudyPlanResponse:
    """Retrieve the active study plan roadmap, schedule groups, and progress."""
    try:
        plan_data = get_active_study_plan(
            db=db,
            user_id=current_user.id,
            course_id=course_id,
        )
        if not plan_data:
            raise PlanNotFoundError(f"No active study plan found for course {course_id}.")
        return StudyPlanResponse(
            success=True,
            data=plan_data,
            message="Active study plan retrieved successfully",
        )
    except CourseNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PlannerError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/study-plans/{plan_id}",
    response_model=StudyPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Get study plan by ID",
)
def get_study_plan_by_id_endpoint(
    plan_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudyPlanResponse:
    """Retrieve a specific version of a study plan by ID."""
    try:
        plan_data = get_study_plan_by_id(
            db=db,
            user_id=current_user.id,
            plan_id=plan_id,
        )
        return StudyPlanResponse(
            success=True,
            data=plan_data,
            message="Study plan retrieved successfully",
        )
    except PlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PlannerError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch(
    "/study-plans/{plan_id}/items/{item_id}",
    response_model=PlanItemResponseEnvelope,
    status_code=status.HTTP_200_OK,
    summary="Update status, duration, or date of a plan session item",
)
def update_plan_item_status_endpoint(
    plan_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: PlanItemUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlanItemResponseEnvelope:
    """Update a study session progress (e.g. mark COMPLETED, IN_PROGRESS, or SKIPPED)."""
    try:
        item = update_plan_item_status(
            db=db,
            user_id=current_user.id,
            plan_id=plan_id,
            item_id=item_id,
            new_status=payload.status,
            new_duration=payload.duration_minutes,
            new_date=payload.scheduled_date,
        )
        return PlanItemResponseEnvelope(
            success=True,
            data=item,
            message="Plan item updated successfully",
        )
    except PlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PlannerError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/study-plans/{plan_id}/rebalance",
    response_model=StudyPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Dynamically rebalance active study plan",
)
def rebalance_study_plan_endpoint(
    plan_id: uuid.UUID,
    payload: Optional[StudyPlanGeneratePayload] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudyPlanResponse:
    """Rebalance remaining sessions preserving completed work."""
    updated_daily = payload.daily_minutes if payload else None
    updated_exam = payload.exam_date if payload else None

    try:
        plan_data = rebalance_learning_plan(
            db=db,
            user_id=current_user.id,
            plan_id=plan_id,
            updated_daily_minutes=updated_daily,
            updated_exam_date=updated_exam,
        )
        return StudyPlanResponse(
            success=True,
            data=plan_data,
            message="Study plan rebalanced successfully",
        )
    except PlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PlannerError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/courses/{course_id}/study-plan/history",
    response_model=StudyPlanHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get historical plan versions for a course",
)
def get_study_plan_history_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudyPlanHistoryResponse:
    """Retrieve all study plan iterations for a course."""
    try:
        history = get_study_plan_history(
            db=db,
            user_id=current_user.id,
            course_id=course_id,
        )
        return StudyPlanHistoryResponse(
            success=True,
            data=history,
            message="Study plan history retrieved successfully",
        )
    except CourseNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PlannerError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
