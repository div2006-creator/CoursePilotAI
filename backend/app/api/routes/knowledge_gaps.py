"""API routes for Knowledge Gap Analysis & Prerequisite Intelligence."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.diagnostic import DiagnosticQuestionsResponse
from app.schemas.knowledge_gap import (
    KnowledgeGapAnalysisResponse,
    KnowledgeGapHistoryResponse,
    ReassessRequest,
    RecommendationsResponse,
    TopicKnowledgeGapResponse,
)
from app.services.diagnostic_service import CourseNotFoundError
from app.services.knowledge_gap_service import (
    AnalysisNotFoundError,
    KnowledgeGapError,
    analyze_knowledge_gaps,
    get_gap_recommendations,
    get_knowledge_gap_history,
    get_latest_knowledge_gap_analysis,
    get_topic_knowledge_gap,
    reassess_unassessed_prerequisites,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/courses/{course_id}/knowledge-gaps/analyze",
    response_model=KnowledgeGapAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger a new knowledge gap and prerequisite intelligence analysis",
)
def trigger_knowledge_gap_analysis_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeGapAnalysisResponse:
    """Analyze student diagnostic performance against the course prerequisite DAG."""
    try:
        data = analyze_knowledge_gaps(
            db=db,
            user_id=current_user.id,
            course_id=course_id,
        )
        return KnowledgeGapAnalysisResponse(
            success=True,
            data=data,
            message="Knowledge gap analysis completed successfully.",
        )
    except CourseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except KnowledgeGapError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/courses/{course_id}/knowledge-gaps",
    response_model=KnowledgeGapAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Get latest knowledge gap analysis for a course",
)
@router.get(
    "/courses/{course_id}/knowledge-gaps/summary",
    response_model=KnowledgeGapAnalysisResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_latest_knowledge_gaps_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeGapAnalysisResponse:
    """Retrieve the most recent saved knowledge gap analysis, or run one if none exists."""
    try:
        data = get_latest_knowledge_gap_analysis(
            db=db,
            user_id=current_user.id,
            course_id=course_id,
        )

        if not data:
            # Run initial analysis automatically
            data = analyze_knowledge_gaps(
                db=db,
                user_id=current_user.id,
                course_id=course_id,
            )

        return KnowledgeGapAnalysisResponse(
            success=True,
            data=data,
            message="Latest knowledge gap analysis retrieved.",
        )
    except CourseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/courses/{course_id}/knowledge-gaps/history",
    response_model=KnowledgeGapHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get historical knowledge gap analysis records for a course",
)
def get_knowledge_gap_history_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeGapHistoryResponse:
    """Retrieve list of previous knowledge gap analyses."""
    try:
        history = get_knowledge_gap_history(
            db=db,
            user_id=current_user.id,
            course_id=course_id,
        )
        return KnowledgeGapHistoryResponse(
            success=True,
            data=history,
            message="Knowledge gap history retrieved.",
        )
    except CourseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/topics/{topic_id}/knowledge-gaps",
    response_model=TopicKnowledgeGapResponse,
    status_code=status.HTTP_200_OK,
    summary="Get detailed knowledge gap status for a specific topic",
)
def get_topic_knowledge_gap_endpoint(
    topic_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TopicKnowledgeGapResponse:
    """Inspect knowledge gap evidence and prerequisite chain for a single topic."""
    gap_detail = get_topic_knowledge_gap(
        db=db,
        user_id=current_user.id,
        topic_id=topic_id,
    )

    return TopicKnowledgeGapResponse(
        success=True,
        data=gap_detail,
        message="Topic knowledge gap details retrieved." if gap_detail else "No active gap identified for this topic.",
    )


@router.get(
    "/courses/{course_id}/knowledge-gaps/recommendations",
    response_model=RecommendationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get prioritized learning recommendations based on knowledge gaps",
)
def get_recommendations_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendationsResponse:
    """Retrieve actionable, prioritized topic recommendations."""
    try:
        recommendations = get_gap_recommendations(
            db=db,
            user_id=current_user.id,
            course_id=course_id,
        )
        return RecommendationsResponse(
            success=True,
            data=recommendations,
            message="Recommendations retrieved successfully.",
        )
    except CourseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/courses/{course_id}/knowledge-gaps/reassess",
    response_model=DiagnosticQuestionsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Launch a targeted diagnostic assessment for unassessed prerequisite topics",
)
def reassess_prerequisites_endpoint(
    course_id: uuid.UUID,
    payload: ReassessRequest = ReassessRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiagnosticQuestionsResponse:
    """Re-uses Part 7 Diagnostic Engine targeting unassessed prerequisite topics."""
    diff = payload.difficulty
    q_count = payload.questions_per_topic

    try:
        return reassess_unassessed_prerequisites(
            db=db,
            user_id=current_user.id,
            course_id=course_id,
            difficulty=diff,
            questions_per_topic=q_count,
        )
    except CourseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except KnowledgeGapError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
