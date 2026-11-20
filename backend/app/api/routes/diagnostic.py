"""API routes for Diagnostic Assessment Engine."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.llm import OllamaConnectionError, OllamaModelNotFoundError
from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.diagnostic import (
    DiagnosticHistoryResponse,
    DiagnosticQuestionsResponse,
    DiagnosticResultResponse,
    DiagnosticStartRequest,
    DiagnosticSubmitRequest,
    QuestionPublicResponse,
)
from app.services.diagnostic_service import (
    CourseNotFoundError,
    DiagnosticError,
    InvalidQuestionSubmissionError,
    InvalidTopicSelectionError,
    NoTopicsFoundError,
    SessionAccessDeniedError,
    SessionAlreadySubmittedError,
    SessionNotFoundError,
    get_course_diagnostic_history,
    get_diagnostic_questions,
    get_diagnostic_result,
    start_diagnostic_session,
    submit_diagnostic,
)
from app.services.question_generation_service import (
    InvalidQuestionDataError,
    QuestionGenerationError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Diagnostic Session Management & Lifecycle
# ---------------------------------------------------------------------------


@router.post(
    "/courses/{course_id}/diagnostic/start",
    response_model=DiagnosticQuestionsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new diagnostic assessment for a course",
)
def start_diagnostic_endpoint(
    course_id: uuid.UUID,
    payload: DiagnosticStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiagnosticQuestionsResponse:
    """Generate or retrieve assessment questions and create a new diagnostic session."""
    try:
        session, questions = start_diagnostic_session(
            db=db,
            user_id=current_user.id,
            course_id=course_id,
            payload=payload,
        )

        public_questions = [
            QuestionPublicResponse(
                id=q.id,
                topic_id=q.topic_id,
                topic_name=q.topic.name if q.topic else "General",
                question=q.question,
                options=q.options if isinstance(q.options, list) else list(q.options),
                difficulty=q.difficulty,
            )
            for q in questions
        ]

        return DiagnosticQuestionsResponse(
            session_id=session.id,
            course_id=session.course_id,
            mode=session.mode,
            status=session.status,
            total_questions=len(public_questions),
            questions=public_questions,
        )

    except CourseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (NoTopicsFoundError, InvalidTopicSelectionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except (OllamaConnectionError, OllamaModelNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except (QuestionGenerationError, InvalidQuestionDataError, DiagnosticError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get(
    "/diagnostic/{diagnostic_id}/questions",
    response_model=DiagnosticQuestionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get questions for an active diagnostic assessment session",
)
def get_diagnostic_questions_endpoint(
    diagnostic_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiagnosticQuestionsResponse:
    """Retrieve sanitized assessment questions without answers or explanations."""
    try:
        session, question_tuples = get_diagnostic_questions(
            db=db,
            user_id=current_user.id,
            session_id=diagnostic_id,
        )

        public_questions = [
            QuestionPublicResponse(
                id=q.id,
                topic_id=q.topic_id,
                topic_name=topic_name,
                question=q.question,
                options=q.options if isinstance(q.options, list) else list(q.options),
                difficulty=q.difficulty,
            )
            for q, topic_name in question_tuples
        ]

        return DiagnosticQuestionsResponse(
            session_id=session.id,
            course_id=session.course_id,
            mode=session.mode,
            status=session.status,
            total_questions=len(public_questions),
            questions=public_questions,
        )

    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SessionAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.post(
    "/diagnostic/{diagnostic_id}/submit",
    response_model=DiagnosticResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit answers for a diagnostic assessment",
)
def submit_diagnostic_endpoint(
    diagnostic_id: uuid.UUID,
    payload: DiagnosticSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiagnosticResultResponse:
    """Evaluate submitted student answers, persist attempts, and return analytical results."""
    try:
        result_data = submit_diagnostic(
            db=db,
            user_id=current_user.id,
            session_id=diagnostic_id,
            payload=payload,
        )

        return DiagnosticResultResponse(
            success=True,
            data=result_data,
            message="Diagnostic assessment completed successfully.",
        )

    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SessionAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except (SessionAlreadySubmittedError, InvalidQuestionSubmissionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except DiagnosticError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/diagnostic/{diagnostic_id}/result",
    response_model=DiagnosticResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Get result analytics and review for a completed diagnostic assessment",
)
def get_diagnostic_result_endpoint(
    diagnostic_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiagnosticResultResponse:
    """Retrieve score, topic-wise accuracy, and detailed question review for a completed session."""
    try:
        result_data = get_diagnostic_result(
            db=db,
            user_id=current_user.id,
            session_id=diagnostic_id,
        )

        return DiagnosticResultResponse(
            success=True,
            data=result_data,
            message="Diagnostic result retrieved successfully.",
        )

    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SessionAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except DiagnosticError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/courses/{course_id}/diagnostic/history",
    response_model=DiagnosticHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get historical diagnostic assessments for a course",
)
def get_diagnostic_history_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiagnosticHistoryResponse:
    """Retrieve list of past diagnostic sessions for this course."""
    try:
        history_items = get_course_diagnostic_history(
            db=db,
            user_id=current_user.id,
            course_id=course_id,
        )

        return DiagnosticHistoryResponse(
            success=True,
            data=history_items,
            message="Diagnostic history retrieved successfully.",
        )

    except CourseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

