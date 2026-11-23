"""API routes for Part 10: Personalized AI Tutor."""
from __future__ import annotations

import logging
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.question import Question
from app.models.topic import Topic
from app.models.user import User
from app.schemas.tutor import (
    HintRequestPayload,
    HintResponse,
    HintResponseData,
    PracticeAnswerSubmitPayload,
    PracticeEvaluationResponse,
    PracticeEvaluationResponseData,
    PracticeQuestionResponse,
    PracticeQuestionResponseData,
    TutorMessageItem,
    TutorMessageListResponse,
    TutorMessageResponse,
    TutorMessageResponseData,
    TutorMessageSendPayload,
    TutorPreferencesUpdatePayload,
    TutorSessionCreatePayload,
    TutorSessionResponse,
    TutorSessionResponseData,
)
from app.services.tutor_practice_service import (
    evaluate_student_answer,
    generate_hint,
    generate_practice_question,
)
from app.services.tutor_service import (
    CourseAccessDeniedError,
    TutorServiceError,
    TutorSessionNotFoundError,
    complete_tutor_session,
    get_session_messages,
    get_tutor_session,
    send_tutor_message,
    start_tutor_session,
    update_tutor_preferences,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/courses/{course_id}/tutor/sessions",
    response_model=TutorSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new personalized AI tutoring session",
)
def start_tutor_session_endpoint(
    course_id: uuid.UUID,
    payload: TutorSessionCreatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TutorSessionResponse:
    """Initialize a tutoring session for a course topic with verified context and opening greeting."""
    try:
        session, first_msg = start_tutor_session(
            db=db,
            user_id=current_user.id,
            course_id=course_id,
            topic_id=payload.topic_id,
            plan_item_id=payload.plan_item_id,
            language=payload.language or "english",
            explanation_level=payload.explanation_level or "intermediate",
        )

        msg_item = TutorMessageItem.model_validate(first_msg)
        session_data = TutorSessionResponseData(
            id=session.id,
            user_id=session.user_id,
            course_id=session.course_id,
            course_title=session.course.title if session.course else "Course",
            topic_id=session.topic_id,
            topic_name=session.topic.name if session.topic else "Topic",
            plan_item_id=session.plan_item_id,
            language=session.language,
            explanation_level=session.explanation_level,
            status=session.status,
            current_stage=session.current_stage,
            created_at=session.created_at,
            updated_at=session.updated_at,
            suggested_next_action="Review orientation or ask a question",
            messages=[msg_item],
        )

        return TutorSessionResponse(
            success=True,
            data=session_data,
            message="Tutoring session initialized successfully",
        )
    except (CourseAccessDeniedError, TutorSessionNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (TutorServiceError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/tutor/sessions/{session_id}",
    response_model=TutorSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get active tutoring session by ID",
)
def get_tutor_session_endpoint(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TutorSessionResponse:
    """Retrieve session state, teaching stage, and message history."""
    try:
        session = get_tutor_session(db, current_user.id, session_id)
        msg_items = [TutorMessageItem.model_validate(m) for m in session.messages]

        session_data = TutorSessionResponseData(
            id=session.id,
            user_id=session.user_id,
            course_id=session.course_id,
            course_title=session.course.title if session.course else "Course",
            topic_id=session.topic_id,
            topic_name=session.topic.name if session.topic else "Topic",
            plan_item_id=session.plan_item_id,
            language=session.language,
            explanation_level=session.explanation_level,
            status=session.status,
            current_stage=session.current_stage,
            created_at=session.created_at,
            updated_at=session.updated_at,
            suggested_next_action="Continue conversation or ask for practice",
            messages=msg_items,
        )

        return TutorSessionResponse(
            success=True,
            data=session_data,
            message="Tutoring session retrieved successfully",
        )
    except TutorSessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/tutor/sessions/{session_id}/messages",
    response_model=TutorMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message to the AI tutor",
)
def send_tutor_message_endpoint(
    session_id: uuid.UUID,
    payload: TutorMessageSendPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TutorMessageResponse:
    """Send student message, advance teaching stage, and generate adaptive response."""
    try:
        asst_msg, session, next_action, sources = send_tutor_message(
            db=db,
            user_id=current_user.id,
            session_id=session_id,
            content=payload.message,
        )

        resp_data = TutorMessageResponseData(
            message=TutorMessageItem.model_validate(asst_msg),
            session_id=session.id,
            current_stage=session.current_stage,
            suggested_next_action=next_action,
            sources=sources,
        )

        return TutorMessageResponse(
            success=True,
            data=resp_data,
            message="Message processed successfully",
        )
    except TutorSessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (TutorServiceError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/tutor/sessions/{session_id}/messages",
    response_model=TutorMessageListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get conversation history for a session",
)
def get_session_messages_endpoint(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TutorMessageListResponse:
    """Retrieve full dialogue history for an active or completed tutoring session."""
    try:
        messages = get_session_messages(db, current_user.id, session_id)
        msg_items = [TutorMessageItem.model_validate(m) for m in messages]

        return TutorMessageListResponse(
            success=True,
            data=msg_items,
            message="Conversation history retrieved successfully",
        )
    except TutorSessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/tutor/sessions/{session_id}/preferences",
    response_model=TutorSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update tutor language and explanation preferences",
)
def update_tutor_preferences_endpoint(
    session_id: uuid.UUID,
    payload: TutorPreferencesUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TutorSessionResponse:
    """Dynamically adjust preferred language (English/Hindi/Hinglish) and explanation level."""
    try:
        session = update_tutor_preferences(
            db=db,
            user_id=current_user.id,
            session_id=session_id,
            language=payload.language,
            explanation_level=payload.explanation_level,
        )

        msg_items = [TutorMessageItem.model_validate(m) for m in session.messages]
        session_data = TutorSessionResponseData(
            id=session.id,
            user_id=session.user_id,
            course_id=session.course_id,
            course_title=session.course.title if session.course else "Course",
            topic_id=session.topic_id,
            topic_name=session.topic.name if session.topic else "Topic",
            plan_item_id=session.plan_item_id,
            language=session.language,
            explanation_level=session.explanation_level,
            status=session.status,
            current_stage=session.current_stage,
            created_at=session.created_at,
            updated_at=session.updated_at,
            suggested_next_action="Continue with updated preferences",
            messages=msg_items,
        )

        return TutorSessionResponse(
            success=True,
            data=session_data,
            message="Tutor preferences updated successfully",
        )
    except TutorSessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/tutor/sessions/{session_id}/practice",
    response_model=PracticeQuestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a targeted practice question for the topic",
)
def generate_practice_question_endpoint(
    session_id: uuid.UUID,
    difficulty: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PracticeQuestionResponse:
    """Generate a conceptual, multiple-choice, or code-tracing practice question."""
    try:
        session = get_tutor_session(db, current_user.id, session_id)
        question = generate_practice_question(
            db=db,
            user_id=current_user.id,
            session=session,
            difficulty=difficulty,
        )

        topic = db.execute(select(Topic).where(Topic.id == session.topic_id)).scalar_one_or_none()
        topic_name = topic.name if topic else "Topic"

        # Sanitize options to list of strings
        opts: List[str] = []
        if question.options and isinstance(question.options, list):
            opts = [str(o) for o in question.options]

        data = PracticeQuestionResponseData(
            id=question.id,
            topic_id=question.topic_id,
            topic_name=topic_name,
            question=question.question,
            options=opts,
            difficulty=question.difficulty,
        )

        return PracticeQuestionResponse(
            success=True,
            data=data,
            message="Practice question generated successfully",
        )
    except TutorSessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (TutorServiceError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/tutor/sessions/{session_id}/practice/{question_id}/submit",
    response_model=PracticeEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit student answer and receive structured evaluation",
)
def submit_practice_answer_endpoint(
    session_id: uuid.UUID,
    question_id: uuid.UUID,
    payload: PracticeAnswerSubmitPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PracticeEvaluationResponse:
    """Evaluate student response, record attempt, and update topic mastery score."""
    try:
        session = get_tutor_session(db, current_user.id, session_id)
        question = db.execute(
            select(Question).where(Question.id == question_id, Question.topic_id == session.topic_id)
        ).scalar_one_or_none()

        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice question not found.")

        eval_res = evaluate_student_answer(
            db=db,
            user_id=current_user.id,
            session=session,
            question=question,
            student_answer=payload.answer,
        )

        data = PracticeEvaluationResponseData(
            question_id=question.id,
            is_correct=eval_res.is_correct,
            score=eval_res.score,
            feedback=eval_res.feedback,
            correct_answer=question.correct_answer,
            explanation=question.explanation,
            strengths=eval_res.strengths,
            errors_identified=eval_res.errors_identified,
            misconceptions=eval_res.misconceptions,
            next_step_advice=eval_res.next_step_advice,
        )

        return PracticeEvaluationResponse(
            success=True,
            data=data,
            message="Practice response evaluated successfully",
        )
    except TutorSessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (TutorServiceError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/tutor/sessions/{session_id}/practice/{question_id}/hint",
    response_model=HintResponse,
    status_code=status.HTTP_200_OK,
    summary="Request a progressive Socratic hint",
)
def request_hint_endpoint(
    session_id: uuid.UUID,
    question_id: uuid.UUID,
    payload: Optional[HintRequestPayload] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HintResponse:
    """Generate progressive Socratic hints without immediately revealing the full answer."""
    try:
        session = get_tutor_session(db, current_user.id, session_id)
        question = db.execute(
            select(Question).where(Question.id == question_id, Question.topic_id == session.topic_id)
        ).scalar_one_or_none()

        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

        level = payload.hint_level if payload else 1
        hint_text = generate_hint(
            db=db,
            session=session,
            question=question,
            hint_level=level,
        )

        data = HintResponseData(
            question_id=question.id,
            hint_level=level,
            hint=hint_text,
        )

        return HintResponse(
            success=True,
            data=data,
            message="Hint generated successfully",
        )
    except TutorSessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/tutor/sessions/{session_id}/complete",
    response_model=TutorSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete tutoring session upon evidence of understanding",
)
def complete_tutor_session_endpoint(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TutorSessionResponse:
    """Mark session as completed and update any associated study plan item."""
    try:
        session = complete_tutor_session(db, current_user.id, session_id)
        msg_items = [TutorMessageItem.model_validate(m) for m in session.messages]

        session_data = TutorSessionResponseData(
            id=session.id,
            user_id=session.user_id,
            course_id=session.course_id,
            course_title=session.course.title if session.course else "Course",
            topic_id=session.topic_id,
            topic_name=session.topic.name if session.topic else "Topic",
            plan_item_id=session.plan_item_id,
            language=session.language,
            explanation_level=session.explanation_level,
            status=session.status,
            current_stage=session.current_stage,
            created_at=session.created_at,
            updated_at=session.updated_at,
            suggested_next_action="Session completed! View your updated learning plan.",
            messages=msg_items,
        )

        return TutorSessionResponse(
            success=True,
            data=session_data,
            message="Tutoring session completed successfully",
        )
    except TutorSessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

