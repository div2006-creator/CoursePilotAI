"""API routes for Learning Analytics and Adaptive Progress Intelligence."""
from __future__ import annotations

import logging
from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.analytics import (
    CourseOverviewResponse,
    ExamReadinessResponse,
    FullAnalyticsDashboardResponse,
    LearningImprovementResponse,
    LearningProgressResponse,
    PrerequisiteBlockerItem,
    PrerequisiteBottlenecksResponse,
    RecommendationsResponse,
    StudyConsistencyResponse,
    TopicMasteryAnalyticsResponse,
)
from app.services.analytics_service import (
    CourseAccessDeniedError,
    get_course_overview,
    get_diagnostic_comparison,
    get_full_dashboard,
    get_learning_progress,
    get_prerequisite_blockers,
    get_recommended_next_actions,
    get_study_consistency,
    get_topic_mastery_analytics,
)
from app.services.exam_readiness_service import calculate_exam_readiness

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/courses/{course_id}/analytics/overview",
    response_model=CourseOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get aggregate learning metrics for a course",
)
def get_course_overview_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CourseOverviewResponse:
    """Retrieve verified topic counts, completed study sessions, practice attempts, and average mastery."""
    try:
        data = get_course_overview(db, current_user.id, course_id)
        return CourseOverviewResponse(
            success=True,
            data=data,
            message="Course overview analytics retrieved successfully",
        )
    except CourseAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Error retrieving course overview analytics: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve course overview.")


@router.get(
    "/courses/{course_id}/analytics/topics",
    response_model=TopicMasteryAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get detailed topic mastery and evidence breakdown",
)
@router.get(
    "/courses/{course_id}/analytics/mastery",
    response_model=TopicMasteryAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_topic_mastery_analytics_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TopicMasteryAnalyticsResponse:
    """Retrieve topic-by-topic mastery scores, previous scores, evidence counts, and prerequisite status."""
    try:
        data = get_topic_mastery_analytics(db, current_user.id, course_id)
        return TopicMasteryAnalyticsResponse(
            success=True,
            data=data,
            message="Topic mastery analytics retrieved successfully",
        )
    except CourseAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Error retrieving topic mastery analytics: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve topic mastery.")


@router.get(
    "/courses/{course_id}/analytics/improvement",
    response_model=LearningImprovementResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare baseline diagnostic against fresh post-learning assessments",
)
def get_learning_improvement_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LearningImprovementResponse:
    """Measure verified learning improvement (percentage-point change) on fresh non-duplicate questions."""
    try:
        data = get_diagnostic_comparison(db, current_user.id, course_id)
        return LearningImprovementResponse(
            success=True,
            data=data,
            message="Diagnostic improvement comparison retrieved successfully",
        )
    except CourseAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Error retrieving learning improvement comparison: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to compute improvement comparison.")


@router.get(
    "/courses/{course_id}/analytics/progress",
    response_model=LearningProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Get learning velocity and longitudinal mastery history",
)
def get_learning_progress_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LearningProgressResponse:
    """Retrieve progress points and 7-day/30-day learning velocity metrics."""
    try:
        data = get_learning_progress(db, current_user.id, course_id)
        return LearningProgressResponse(
            success=True,
            data=data,
            message="Learning progress and velocity retrieved successfully",
        )
    except CourseAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Error retrieving learning progress: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve learning progress.")


@router.get(
    "/courses/{course_id}/analytics/consistency",
    response_model=StudyConsistencyResponse,
    status_code=status.HTTP_200_OK,
    summary="Get study consistency, completion rates, and streak",
)
def get_study_consistency_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudyConsistencyResponse:
    """Retrieve scheduled vs completed study sessions, active calendar days, and honest consecutive streak."""
    try:
        data = get_study_consistency(db, current_user.id, course_id)
        return StudyConsistencyResponse(
            success=True,
            data=data,
            message="Study consistency data retrieved successfully",
        )
    except CourseAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Error retrieving study consistency: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve study consistency.")


@router.get(
    "/courses/{course_id}/analytics/exam-readiness",
    response_model=ExamReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Get explainable exam readiness score and component breakdown",
)
def get_exam_readiness_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExamReadinessResponse:
    """Calculate transparent readiness score based on mastery, topic importance, prerequisites, and coverage."""
    try:
        data = calculate_exam_readiness(db, current_user.id, course_id)
        return ExamReadinessResponse(
            success=True,
            data=data,
            message="Exam readiness score calculated successfully",
        )
    except CourseAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Error calculating exam readiness: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to calculate exam readiness.")


@router.get(
    "/courses/{course_id}/analytics/bottlenecks",
    response_model=PrerequisiteBottlenecksResponse,
    status_code=status.HTTP_200_OK,
    summary="Identify weak foundational topics blocking dependent concepts",
)
def get_prerequisite_bottlenecks_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PrerequisiteBottlenecksResponse:
    """Detect knowledge graph bottleneck topics that prevent mastery in downstream units."""
    try:
        data = get_prerequisite_blockers(db, current_user.id, course_id)
        return PrerequisiteBottlenecksResponse(
            success=True,
            data=data,
            message="Prerequisite bottlenecks identified successfully",
        )
    except CourseAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Error retrieving prerequisite bottlenecks: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to identify bottlenecks.")


@router.get(
    "/courses/{course_id}/analytics/recommendations",
    response_model=RecommendationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get prioritized, deterministic learning action recommendations",
)
def get_recommendations_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendationsResponse:
    """Generate explainable next steps based on bottlenecks, developing topics, and exam proximity."""
    try:
        data = get_recommended_next_actions(db, current_user.id, course_id)
        return RecommendationsResponse(
            success=True,
            data=data,
            message="Learning recommendations generated successfully",
        )
    except CourseAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Error generating recommendations: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate recommendations.")


@router.get(
    "/courses/{course_id}/analytics",
    response_model=FullAnalyticsDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get full learning analytics dashboard payload",
)
@router.get(
    "/courses/{course_id}/analytics/dashboard",
    response_model=FullAnalyticsDashboardResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_full_analytics_dashboard_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FullAnalyticsDashboardResponse:
    """Retrieve complete analytics dashboard including overview, mastery, improvement, consistency, readiness, and actions."""
    try:
        data = get_full_dashboard(db, current_user.id, course_id)
        return FullAnalyticsDashboardResponse(
            success=True,
            data=data,
            message="Full analytics dashboard retrieved successfully",
        )
    except CourseAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Error retrieving full analytics dashboard: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve analytics dashboard.")

