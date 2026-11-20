"""Service orchestrating diagnostic assessments, student attempts, and results."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Callable, List, Optional, Tuple
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import utc_now
from app.models.attempt import Attempt
from app.models.course import Course
from app.models.diagnostic_session import DiagnosticSession, DiagnosticSessionQuestion
from app.models.question import Question
from app.models.topic import Topic
from app.schemas.diagnostic import (
    DiagnosticHistoryItem,
    DiagnosticResultData,
    DiagnosticStartRequest,
    DiagnosticSubmitRequest,
    QuestionReviewItem,
)
from app.services.assessment_analytics_service import (
    calculate_difficulty_breakdown,
    calculate_diagnostic_score,
    calculate_topic_wise_accuracy,
    identify_strong_and_weak_topics,
)
from app.services.question_generation_service import generate_questions_for_topics

logger = logging.getLogger(__name__)


def _calculate_duration(
    attempts_duration: int,
    started_at: Optional[datetime],
    completed_at: Optional[datetime],
) -> int:
    if attempts_duration > 0:
        return attempts_duration
    if started_at and completed_at:
        s_at = started_at if started_at.tzinfo else started_at.replace(tzinfo=timezone.utc)
        c_at = completed_at if completed_at.tzinfo else completed_at.replace(tzinfo=timezone.utc)
        return max(0, int((c_at - s_at).total_seconds()))
    return 0


class DiagnosticError(Exception):
    """Base exception for diagnostic assessment operations."""


class CourseNotFoundError(DiagnosticError):
    """Raised when the specified course does not exist or user lacks access."""


class SessionNotFoundError(DiagnosticError):
    """Raised when the requested diagnostic session is not found."""


class SessionAccessDeniedError(DiagnosticError):
    """Raised when a user attempts to access another user's session."""


class NoTopicsFoundError(DiagnosticError):
    """Raised when a course has no extracted topics available for testing."""


class InvalidTopicSelectionError(DiagnosticError):
    """Raised when requested topics do not belong to the target course."""


class SessionAlreadySubmittedError(DiagnosticError):
    """Raised when attempting to submit an already completed session."""


class InvalidQuestionSubmissionError(DiagnosticError):
    """Raised when submission includes question IDs that do not belong to the session."""


def start_diagnostic_session(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
    payload: DiagnosticStartRequest,
    llm_generator: Optional[Callable[..., str]] = None,
) -> Tuple[DiagnosticSession, List[Question]]:
    """Initiate a new diagnostic assessment session for a course."""
    # 1. Verify course ownership
    course = db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user_id)
    ).scalar_one_or_none()

    if not course:
        raise CourseNotFoundError("Course not found or access denied.")

    # 2. Select topics
    if payload.mode == "selected":
        if not payload.topic_ids:
            raise InvalidTopicSelectionError("Topic IDs must be provided when mode is 'selected'.")

        target_topics = list(
            db.execute(
                select(Topic).where(
                    Topic.course_id == course_id,
                    Topic.id.in_(payload.topic_ids),
                )
            ).scalars().all()
        )

        if len(target_topics) != len(set(payload.topic_ids)):
            raise InvalidTopicSelectionError("One or more selected topics do not belong to this course.")
    else:
        # Full diagnostic: select all root topics (or all topics if no hierarchy)
        target_topics = list(
            db.execute(
                select(Topic)
                .where(Topic.course_id == course_id, Topic.parent_id.is_(None))
                .order_by(Topic.created_at, Topic.name)
            ).scalars().all()
        )
        if not target_topics:
            target_topics = list(
                db.execute(
                    select(Topic)
                    .where(Topic.course_id == course_id)
                    .order_by(Topic.created_at, Topic.name)
                ).scalars().all()
            )

    if not target_topics:
        raise NoTopicsFoundError(
            "Course has no topics available for diagnostic assessment. "
            "Please extract topics from your syllabus first."
        )

    # 3. Generate or retrieve questions
    questions = generate_questions_for_topics(
        db=db,
        course_id=course_id,
        topics=target_topics,
        difficulty=payload.difficulty,
        count_per_topic=payload.questions_per_topic,
        llm_generator=llm_generator,
    )

    if not questions:
        raise DiagnosticError("Failed to generate or retrieve diagnostic assessment questions.")

    # 4. Create diagnostic session
    session = DiagnosticSession(
        user_id=user_id,
        course_id=course_id,
        mode=payload.mode,
        status="in_progress",
        total_questions=len(questions),
        correct_answers=0,
        score=0.0,
        started_at=utc_now(),
    )
    db.add(session)
    db.flush()

    # 5. Link questions to session with explicit ordering
    for idx, q in enumerate(questions):
        link = DiagnosticSessionQuestion(
            session_id=session.id,
            question_id=q.id,
            order=idx,
        )
        db.add(link)

    db.commit()
    db.refresh(session)

    return session, questions


def get_diagnostic_questions(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> Tuple[DiagnosticSession, List[Tuple[Question, str]]]:
    """Retrieve the questions for an active diagnostic session.

    Returns:
        (DiagnosticSession, List[(Question, topic_name)])
    """
    session = db.execute(
        select(DiagnosticSession)
        .where(DiagnosticSession.id == session_id)
        .options(
            selectinload(DiagnosticSession.session_questions)
            .selectinload(DiagnosticSessionQuestion.question)
            .selectinload(Question.topic)
        )
    ).scalar_one_or_none()

    if not session:
        raise SessionNotFoundError("Diagnostic session not found.")

    if session.user_id != user_id:
        raise SessionAccessDeniedError("Access to this diagnostic session is denied.")

    # Return questions with topic names
    question_tuples: List[Tuple[Question, str]] = []
    sorted_sq = sorted(session.session_questions, key=lambda sq: sq.order)
    for sq in sorted_sq:
        q = sq.question
        t_name = q.topic.name if q.topic else "General"
        question_tuples.append((q, t_name))

    return session, question_tuples


def submit_diagnostic(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    payload: DiagnosticSubmitRequest,
) -> DiagnosticResultData:
    """Evaluate and store submitted diagnostic answers, generating full analytics."""
    session = db.execute(
        select(DiagnosticSession)
        .where(DiagnosticSession.id == session_id)
        .options(
            selectinload(DiagnosticSession.session_questions)
            .selectinload(DiagnosticSessionQuestion.question)
            .selectinload(Question.topic)
        )
    ).scalar_one_or_none()

    if not session:
        raise SessionNotFoundError("Diagnostic session not found.")

    if session.user_id != user_id:
        raise SessionAccessDeniedError("Access to this diagnostic session is denied.")

    if session.status == "completed":
        raise SessionAlreadySubmittedError("Diagnostic session has already been completed and submitted.")

    # Validate submitted question IDs
    session_q_map = {sq.question_id: sq.question for sq in session.session_questions}
    submitted_q_ids = [a.question_id for a in payload.answers]

    if len(submitted_q_ids) != len(set(submitted_q_ids)):
        raise InvalidQuestionSubmissionError("Duplicate answers submitted for the same question.")

    for q_id in submitted_q_ids:
        if q_id not in session_q_map:
            raise InvalidQuestionSubmissionError(
                f"Question ID {q_id} does not belong to this diagnostic session."
            )

    submission_dict = {a.question_id: a for a in payload.answers}
    created_attempts: List[Attempt] = []
    review_items: List[QuestionReviewItem] = []
    correct_count = 0

    sorted_sq = sorted(session.session_questions, key=lambda sq: sq.order)
    topics_map: dict[uuid.UUID, Topic] = {}

    for sq in sorted_sq:
        q = sq.question
        topic = q.topic
        if topic and topic.id not in topics_map:
            topics_map[topic.id] = topic

        sub = submission_dict.get(q.id)
        if sub:
            selected = sub.selected_answer.strip()
            time_taken = sub.time_taken
        else:
            selected = ""
            time_taken = 0

        # Exact case-tolerant match
        is_correct = bool(selected and selected.lower() == q.correct_answer.strip().lower())
        if is_correct:
            correct_count += 1

        attempt = Attempt(
            user_id=user_id,
            course_id=session.course_id,
            topic_id=q.topic_id,
            question_id=q.id,
            diagnostic_session_id=session.id,
            selected_answer=selected,
            is_correct=is_correct,
            time_taken=time_taken,
        )
        db.add(attempt)
        created_attempts.append(attempt)

        review_items.append(
            QuestionReviewItem(
                question_id=q.id,
                topic_id=q.topic_id,
                topic_name=topic.name if topic else "General",
                question=q.question,
                options=q.options if isinstance(q.options, list) else list(q.options),
                selected_answer=selected,
                correct_answer=q.correct_answer,
                is_correct=is_correct,
                explanation=q.explanation,
                time_taken=time_taken,
            )
        )

    total_q = len(session.session_questions)
    final_score = calculate_diagnostic_score(correct_count, total_q)

    # Update session status
    session.status = "completed"
    session.total_questions = total_q
    session.correct_answers = correct_count
    session.score = final_score
    session.completed_at = utc_now()

    db.commit()

    # Calculate analytics
    topic_accuracies = calculate_topic_wise_accuracy(created_attempts, topics_map)
    diff_breakdown = calculate_difficulty_breakdown(created_attempts, session_q_map)
    strong_topics, weak_topics = identify_strong_and_weak_topics(topic_accuracies)

    duration = _calculate_duration(
        sum(a.time_taken for a in created_attempts),
        session.started_at,
        session.completed_at,
    )

    return DiagnosticResultData(
        session_id=session.id,
        course_id=session.course_id,
        mode=session.mode,
        status=session.status,
        score=session.score,
        total_questions=total_q,
        correct_answers=correct_count,
        incorrect_answers=total_q - correct_count,
        duration_seconds=duration,
        topic_accuracies=topic_accuracies,
        difficulty_breakdown=diff_breakdown,
        strongest_topics=strong_topics,
        weak_topics=weak_topics,
        questions_review=review_items,
    )


def get_diagnostic_result(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> DiagnosticResultData:
    """Retrieve full diagnostic result and question review for a completed session."""
    session = db.execute(
        select(DiagnosticSession)
        .where(DiagnosticSession.id == session_id)
        .options(
            selectinload(DiagnosticSession.session_questions)
            .selectinload(DiagnosticSessionQuestion.question)
            .selectinload(Question.topic),
            selectinload(DiagnosticSession.attempts),
        )
    ).scalar_one_or_none()

    if not session:
        raise SessionNotFoundError("Diagnostic session not found.")

    if session.user_id != user_id:
        raise SessionAccessDeniedError("Access to this diagnostic session is denied.")

    if session.status != "completed":
        raise DiagnosticError("Diagnostic assessment has not been completed yet.")

    session_q_map = {sq.question_id: sq.question for sq in session.session_questions}
    attempts_map = {a.question_id: a for a in session.attempts}
    topics_map: dict[uuid.UUID, Topic] = {}

    review_items: List[QuestionReviewItem] = []
    sorted_sq = sorted(session.session_questions, key=lambda sq: sq.order)

    for sq in sorted_sq:
        q = sq.question
        topic = q.topic
        if topic and topic.id not in topics_map:
            topics_map[topic.id] = topic

        att = attempts_map.get(q.id)
        selected = att.selected_answer if att else ""
        is_corr = att.is_correct if att else False
        time_t = att.time_taken if att else 0

        review_items.append(
            QuestionReviewItem(
                question_id=q.id,
                topic_id=q.topic_id,
                topic_name=topic.name if topic else "General",
                question=q.question,
                options=q.options if isinstance(q.options, list) else list(q.options),
                selected_answer=selected,
                correct_answer=q.correct_answer,
                is_correct=is_corr,
                explanation=q.explanation,
                time_taken=time_t,
            )
        )

    topic_accuracies = calculate_topic_wise_accuracy(session.attempts, topics_map)
    diff_breakdown = calculate_difficulty_breakdown(session.attempts, session_q_map)
    strong_topics, weak_topics = identify_strong_and_weak_topics(topic_accuracies)

    duration = _calculate_duration(
        sum(a.time_taken for a in session.attempts),
        session.started_at,
        session.completed_at,
    )

    return DiagnosticResultData(
        session_id=session.id,
        course_id=session.course_id,
        mode=session.mode,
        status=session.status,
        score=session.score,
        total_questions=session.total_questions,
        correct_answers=session.correct_answers,
        incorrect_answers=session.total_questions - session.correct_answers,
        duration_seconds=duration,
        topic_accuracies=topic_accuracies,
        difficulty_breakdown=diff_breakdown,
        strongest_topics=strong_topics,
        weak_topics=weak_topics,
        questions_review=review_items,
    )


def get_course_diagnostic_history(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
) -> List[DiagnosticHistoryItem]:
    """Retrieve historical diagnostic assessment runs for a course."""
    course = db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user_id)
    ).scalar_one_or_none()

    if not course:
        raise CourseNotFoundError("Course not found or access denied.")

    sessions = list(
        db.execute(
            select(DiagnosticSession)
            .where(
                DiagnosticSession.course_id == course_id,
                DiagnosticSession.user_id == user_id,
            )
            .order_by(DiagnosticSession.created_at.desc())
        ).scalars().all()
    )

    return [
        DiagnosticHistoryItem(
            session_id=s.id,
            course_id=s.course_id,
            mode=s.mode,
            status=s.status,
            score=s.score,
            total_questions=s.total_questions,
            correct_answers=s.correct_answers,
            started_at=s.started_at,
            completed_at=s.completed_at,
        )
        for s in sessions
    ]
