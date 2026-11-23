"""Personalized Tutor Context Tool.

Retrieves and constructs verified student learning context:
topic metadata, prerequisite statuses, measured diagnostic accuracy,
topic mastery scores, recent mistakes, learning plan alignment,
and retrieved course material excerpts.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import logging
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.attempt import Attempt
from app.models.course import Course
from app.models.plan_item import PlanItem
from app.models.question import Question
from app.models.topic import Topic
from app.models.topic_mastery import TopicMastery
from app.models.tutor_session import TutorSession
from app.services.knowledge_gap_service import (
    build_course_prerequisite_maps,
    get_topic_performance,
)
from app.services.retrieval_service import retrieve_topic_context

logger = logging.getLogger(__name__)


@dataclass
class PrerequisiteStatus:
    topic_id: str
    topic_name: str
    knowledge_status: str  # 'strong', 'developing', 'weak', 'not_assessed'
    accuracy_percentage: float
    is_failing: bool


@dataclass
class MistakeRecord:
    question_text: str
    selected_answer: str
    correct_answer: str
    difficulty: str


@dataclass
class TutorContext:
    # Course Metadata
    course_id: str
    course_title: str
    course_description: Optional[str]

    # Current Topic Metadata
    topic_id: str
    topic_name: str
    topic_description: Optional[str]
    topic_difficulty: str
    unit_name: Optional[str]

    # Prerequisite Chain
    prerequisites: List[PrerequisiteStatus]
    has_unmastered_prerequisites: bool
    failing_prerequisites_names: List[str]

    # Student Measured Knowledge
    mastery_score: float  # 0.0 to 1.0 from TopicMastery
    confidence_score: float
    topic_accuracy_percentage: float
    total_attempts_count: int
    knowledge_status: str  # 'strong', 'developing', 'weak', 'not_assessed'

    # Learning History & Mistakes
    recent_mistakes: List[MistakeRecord]
    has_prior_attempts: bool

    # Active Study Plan Item (if session is tied to one)
    plan_item_id: Optional[str]
    plan_session_type: Optional[str]
    plan_priority_score: Optional[float]

    # RAG Retrieved Syllabus / Notes Content
    retrieved_content: str
    sources: List[Dict[str, Any]]

    # Student Preferences
    language: str  # 'english', 'hindi', 'hinglish'
    explanation_level: str  # 'beginner', 'intermediate', 'advanced'
    current_stage: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_tutor_context(
    db: Session,
    user_id: uuid.UUID,
    session: TutorSession,
    topic: Topic,
) -> TutorContext:
    """Construct verified student learning context.

    Strictly reads authenticated user data and course records. Never invents attempts or mastery.
    """
    course = db.execute(
        select(Course).where(Course.id == session.course_id, Course.user_id == user_id)
    ).scalar_one_or_none()

    course_title = course.title if course else "Course"
    course_desc = course.description if course else None

    # 1. Measured Performance & Diagnostic Accuracy
    performances = get_topic_performance(db, user_id, session.course_id)
    topic_perf = performances.get(topic.id)

    if topic_perf:
        k_status = topic_perf.knowledge_status
        accuracy = topic_perf.accuracy_percentage
        attempts_count = topic_perf.total_attempts
    else:
        k_status = "not_assessed"
        accuracy = 0.0
        attempts_count = 0

    # 2. Topic Mastery Record
    mastery_row = db.execute(
        select(TopicMastery).where(
            TopicMastery.user_id == user_id,
            TopicMastery.topic_id == topic.id,
        )
    ).scalar_one_or_none()

    m_score = mastery_row.mastery_score if mastery_row else (accuracy / 100.0 if attempts_count > 0 else 0.0)
    c_score = mastery_row.confidence_score if mastery_row else (topic_perf.confidence_score if topic_perf else 0.0)

    # 3. Prerequisite Graph & Ancestors Status
    prereqs_map, _ = build_course_prerequisite_maps(db, session.course_id)
    direct_prereq_ids = prereqs_map.get(topic.id, [])

    prereq_statuses: List[PrerequisiteStatus] = []
    failing_prereqs: List[str] = []

    for p_id in direct_prereq_ids:
        p_topic = db.execute(select(Topic).where(Topic.id == p_id)).scalar_one_or_none()
        if not p_topic:
            continue
        p_perf = performances.get(p_id)
        if p_perf:
            p_status = p_perf.knowledge_status
            p_acc = p_perf.accuracy_percentage
        else:
            p_status = "not_assessed"
            p_acc = 0.0

        is_fail = p_status in ("weak", "not_assessed")
        if is_fail:
            failing_prereqs.append(p_topic.name)

        prereq_statuses.append(
            PrerequisiteStatus(
                topic_id=str(p_id),
                topic_name=p_topic.name,
                knowledge_status=p_status,
                accuracy_percentage=p_acc,
                is_failing=is_fail,
            )
        )

    # 4. Recent Mistakes
    recent_attempts = list(
        db.execute(
            select(Attempt, Question)
            .join(Question, Question.id == Attempt.question_id)
            .where(
                Attempt.user_id == user_id,
                Attempt.topic_id == topic.id,
                Attempt.is_correct == False,
            )
            .order_by(desc(Attempt.created_at))
            .limit(3)
        ).all()
    )

    mistakes: List[MistakeRecord] = []
    for att, q in recent_attempts:
        mistakes.append(
            MistakeRecord(
                question_text=q.question,
                selected_answer=att.selected_answer,
                correct_answer=q.correct_answer,
                difficulty=q.difficulty or "medium",
            )
        )

    # 5. Study Plan Item Link
    plan_item = None
    if session.plan_item_id:
        plan_item = db.execute(
            select(PlanItem).where(PlanItem.id == session.plan_item_id)
        ).scalar_one_or_none()

    # 6. RAG Document Retrieval
    retrieved_content, sources = retrieve_topic_context(db, session.course_id, topic, limit=3)

    return TutorContext(
        course_id=str(session.course_id),
        course_title=course_title,
        course_description=course_desc,
        topic_id=str(topic.id),
        topic_name=topic.name,
        topic_description=topic.description,
        topic_difficulty=topic.difficulty or "medium",
        unit_name=topic.unit_name,
        prerequisites=prereq_statuses,
        has_unmastered_prerequisites=len(failing_prereqs) > 0,
        failing_prerequisites_names=failing_prereqs,
        mastery_score=round(m_score, 2),
        confidence_score=round(c_score, 2),
        topic_accuracy_percentage=round(accuracy, 1),
        total_attempts_count=attempts_count,
        knowledge_status=k_status,
        recent_mistakes=mistakes,
        has_prior_attempts=attempts_count > 0,
        plan_item_id=str(plan_item.id) if plan_item else None,
        plan_session_type=plan_item.session_type if plan_item else None,
        plan_priority_score=round(plan_item.priority_score, 1) if plan_item else None,
        retrieved_content=retrieved_content,
        sources=sources,
        language=session.language.lower(),
        explanation_level=session.explanation_level.lower(),
        current_stage=session.current_stage,
    )


def format_tutor_context_prompt(ctx: TutorContext) -> str:
    """Format structured learning context into concise guidance for the tutor system prompt."""
    lines = [
        f"### STUDENT LEARNING CONTEXT ###",
        f"- Course: {ctx.course_title}",
        f"- Target Topic: {ctx.topic_name} (Unit: {ctx.unit_name or 'General'}, Difficulty: {ctx.topic_difficulty})",
        f"- Preferred Language: {ctx.language.upper()}",
        f"- Explanation Level: {ctx.explanation_level.upper()}",
        f"- Current Teaching Stage: {ctx.current_stage}",
    ]

    # Measured Mastery Facts
    if ctx.has_prior_attempts:
        lines.append(
            f"- Topic Diagnostic Accuracy: {ctx.topic_accuracy_percentage}% ({ctx.total_attempts_count} attempts, Status: {ctx.knowledge_status.upper()})"
        )
        lines.append(f"- Topic Mastery Score: {int(ctx.mastery_score * 100)}%")
    else:
        lines.append(
            "- Diagnostic Status: Not yet assessed on this topic. Start by assessing baseline intuition."
        )

    # Prerequisite Gaps
    if ctx.has_unmastered_prerequisites:
        failing_str = ", ".join(ctx.failing_prerequisites_names)
        lines.append(
            f"- CRITICAL PREREQUISITE WARNING: The student has weak or unassessed foundational concepts: [{failing_str}]. Address the missing foundational intuition before deep-diving into {ctx.topic_name}."
        )
    else:
        lines.append("- Prerequisite Foundation: Foundational concepts are satisfied.")

    # Recent Mistakes
    if ctx.recent_mistakes:
        lines.append("- Recent Student Mistakes:")
        for m in ctx.recent_mistakes:
            lines.append(f"  * Question: \"{m.question_text[:120]}...\" -> Selected: \"{m.selected_answer}\" (Correct was: \"{m.correct_answer}\")")

    # Retrieved Syllabus / Textbook Context
    if ctx.retrieved_content:
        lines.append(f"\n{ctx.retrieved_content}")

    lines.append("#################################")
    return "\n".join(lines)

