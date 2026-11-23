"""Exam Readiness Engine for CoursePilot AI.

Calculates an explainable, deterministic exam readiness score combining topic mastery,
topic importance, prerequisite readiness, recent assessment performance, and syllabus coverage.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional, Set, Tuple
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import utc_now
from app.models.attempt import Attempt
from app.models.course import Course
from app.models.topic import Topic
from app.models.topic_mastery import TopicMastery
from app.models.topic_prerequisite import TopicPrerequisite
from app.schemas.analytics import ExamReadinessResponseData

# Configurable Scoring Weights (Must sum to 1.0)
WEIGHT_TOPIC_MASTERY = 0.40
WEIGHT_TOPIC_IMPORTANCE = 0.20
WEIGHT_PREREQUISITE_READINESS = 0.15
WEIGHT_RECENT_PERFORMANCE = 0.15
WEIGHT_ASSESSMENT_COVERAGE = 0.10

# Minimum coverage threshold to deem the score reliable
RELIABILITY_COVERAGE_THRESHOLD = 40.0  # Percentage


def calculate_exam_readiness(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
) -> ExamReadinessResponseData:
    """Calculate an explainable exam readiness score for a student and course.

    Guarantees:
    - 100% deterministic calculation (no LLM guesswork).
    - Transparent weight component breakdown.
    - Explicit reliability flag if assessment coverage is below 40%.
    - No fabricated countdown if exam date is not set.
    """
    course = db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user_id)
    ).scalar_one_or_none()

    if not course:
        raise ValueError(f"Course {course_id} not found or access denied.")

    # 1. Fetch all course topics
    topics = db.execute(
        select(Topic).where(Topic.course_id == course_id)
    ).scalars().all()
    total_topics = len(topics)

    if total_topics == 0:
        return ExamReadinessResponseData(
            readiness_score=0.0,
            category="Needs More Practice",
            is_reliable=False,
            assessment_coverage_percentage=0.0,
            coverage_warning="This course does not have any topics yet.",
            mastery_component=0.0,
            importance_component=0.0,
            prerequisite_component=0.0,
            recent_performance_component=0.0,
            coverage_component=0.0,
            exam_date=None,
            days_remaining=None,
            strong_topics_count=0,
            weak_topics_count=0,
            unassessed_topics_count=0,
            blocking_prerequisites_count=0,
            recommended_actions=["Upload course syllabus to extract topics."],
        )

    topic_ids = [t.id for t in topics]

    # 2. Fetch TopicMastery for these topics
    masteries = db.execute(
        select(TopicMastery).where(
            TopicMastery.user_id == user_id,
            TopicMastery.topic_id.in_(topic_ids),
        )
    ).scalars().all()
    mastery_map: Dict[uuid.UUID, float] = {m.topic_id: m.mastery_score for m in masteries}

    # 3. Fetch all Attempts for this user & course
    attempts = db.execute(
        select(Attempt)
        .where(Attempt.user_id == user_id, Attempt.course_id == course_id)
        .order_by(Attempt.created_at.desc())
    ).scalars().all()

    assessed_topic_ids: Set[uuid.UUID] = {a.topic_id for a in attempts}
    # Also include topics with explicit mastery >= 0.0 if created
    for m in masteries:
        assessed_topic_ids.add(m.topic_id)

    assessed_count = len(assessed_topic_ids)
    coverage_pct = round((assessed_count / total_topics) * 100.0, 1)

    # 4. Fetch prerequisite graph for topic importance & readiness
    prereqs = db.execute(
        select(TopicPrerequisite).where(
            TopicPrerequisite.topic_id.in_(topic_ids),
            TopicPrerequisite.prerequisite_id.in_(topic_ids),
        )
    ).scalars().all()

    # Dependents count per topic (structural importance)
    dependents_count_map: Dict[uuid.UUID, int] = {t.id: 0 for t in topics}
    prereqs_of_topic: Dict[uuid.UUID, List[uuid.UUID]] = {t.id: [] for t in topics}
    for p in prereqs:
        dependents_count_map[p.prerequisite_id] = dependents_count_map.get(p.prerequisite_id, 0) + 1
        prereqs_of_topic[p.topic_id].append(p.prerequisite_id)

    # Classify topics: STRONG (>= 80%), DEVELOPING (50-79%), WEAK (< 50%), UNASSESSED
    strong_topics: List[str] = []
    weak_topics: List[str] = []
    unassessed_topics: List[str] = []
    blocking_prereqs_count = 0

    for t in topics:
        if t.id not in assessed_topic_ids:
            unassessed_topics.append(t.name)
        else:
            score = mastery_map.get(t.id, 0.0)
            if score >= 0.80:
                strong_topics.append(t.name)
            elif score < 0.50:
                weak_topics.append(t.name)
                # Check if this weak topic blocks any dependent
                if dependents_count_map.get(t.id, 0) > 0:
                    blocking_prereqs_count += 1

    # --- Component 1: Topic Mastery (40%) ---
    if assessed_count > 0:
        avg_mastery = sum(mastery_map.get(tid, 0.0) for tid in assessed_topic_ids) / assessed_count
    else:
        avg_mastery = 0.0
    mastery_component = round(WEIGHT_TOPIC_MASTERY * avg_mastery * 100.0, 1)

    # --- Component 2: Topic Importance Coverage (20%) ---
    # High-importance topics (those with multiple dependents) carry higher weight
    total_importance_weight = 0.0
    weighted_mastery_sum = 0.0
    for t in topics:
        dep_count = dependents_count_map.get(t.id, 0)
        # Structural weight: base 1 + 0.5 per dependent
        imp_weight = 1.0 + (dep_count * 0.5)
        total_importance_weight += imp_weight
        t_mastery = mastery_map.get(t.id, 0.0) if t.id in assessed_topic_ids else 0.0
        weighted_mastery_sum += (t_mastery * imp_weight)

    importance_ratio = (weighted_mastery_sum / total_importance_weight) if total_importance_weight > 0 else 0.0
    importance_component = round(WEIGHT_TOPIC_IMPORTANCE * importance_ratio * 100.0, 1)

    # --- Component 3: Prerequisite Readiness (15%) ---
    # Proportion of prerequisite dependencies that are satisfied (prereq mastery >= 0.50)
    total_edges = len(prereqs)
    if total_edges > 0:
        satisfied_edges = 0
        for p in prereqs:
            prereq_mastery = mastery_map.get(p.prerequisite_id, 0.0) if p.prerequisite_id in assessed_topic_ids else 0.0
            if prereq_mastery >= 0.50:
                satisfied_edges += 1
        prereq_ratio = satisfied_edges / total_edges
    else:
        prereq_ratio = 1.0  # No prerequisites in syllabus
    prerequisite_component = round(WEIGHT_PREREQUISITE_READINESS * prereq_ratio * 100.0, 1)

    # --- Component 4: Recent Assessment Performance (15%) ---
    # Last 15 attempts (recent form)
    recent_attempts = attempts[:15]
    if recent_attempts:
        recent_accuracy = sum(1 for a in recent_attempts if a.is_correct) / len(recent_attempts)
    else:
        recent_accuracy = avg_mastery
    recent_performance_component = round(WEIGHT_RECENT_PERFORMANCE * recent_accuracy * 100.0, 1)

    # --- Component 5: Assessment Coverage (10%) ---
    coverage_ratio = assessed_count / total_topics
    coverage_component = round(WEIGHT_ASSESSMENT_COVERAGE * coverage_ratio * 100.0, 1)

    # Overall Readiness Score
    raw_readiness = (
        mastery_component
        + importance_component
        + prerequisite_component
        + recent_performance_component
        + coverage_component
    )
    readiness_score = round(min(100.0, max(0.0, raw_readiness)), 1)

    # Reliability & Caveats
    is_reliable = coverage_pct >= RELIABILITY_COVERAGE_THRESHOLD
    coverage_warning = None
    if not is_reliable:
        coverage_warning = (
            f"Assessment coverage is {coverage_pct}%. Readiness score is provisional "
            f"and requires assessing at least {int(RELIABILITY_COVERAGE_THRESHOLD)}% of topics for high reliability."
        )

    # Category Classification
    if readiness_score >= 85.0:
        category = "Exam Ready"
    elif readiness_score >= 70.0:
        category = "Almost Ready"
    elif readiness_score >= 50.0:
        category = "Needs More Practice"
    else:
        category = "At Risk"

    # Exam date handling (no fabricated date!)
    exam_date_str = None
    days_remaining = None
    if course.exam_date:
        exam_date_str = course.exam_date.isoformat()
        today = date.today()
        days_remaining = (course.exam_date - today).days

    # Recommended Actions based on real state
    recommended_actions: List[str] = []
    if blocking_prereqs_count > 0:
        recommended_actions.append(
            f"Focus on {blocking_prereqs_count} weak foundational topic(s) blocking downstream progress."
        )
    if unassessed_topics:
        recommended_actions.append(
            f"Take diagnostic assessments for {len(unassessed_topics)} unassessed topic(s) to improve coverage."
        )
    if weak_topics:
        recommended_actions.append(
            f"Launch AI Tutor practice sessions on weak topics ({', '.join(weak_topics[:3])})."
        )
    if days_remaining is not None and 0 <= days_remaining <= 14:
        recommended_actions.append(
            f"Exam is in {days_remaining} day(s). Prioritize final review sessions."
        )
    if not recommended_actions:
        recommended_actions.append("Keep practicing with periodic mixed-topic mock assessments.")

    return ExamReadinessResponseData(
        readiness_score=readiness_score,
        category=category,
        is_reliable=is_reliable,
        assessment_coverage_percentage=coverage_pct,
        coverage_warning=coverage_warning,
        mastery_component=mastery_component,
        importance_component=importance_component,
        prerequisite_component=prerequisite_component,
        recent_performance_component=recent_performance_component,
        coverage_component=coverage_component,
        exam_date=exam_date_str,
        days_remaining=days_remaining,
        strong_topics_count=len(strong_topics),
        weak_topics_count=len(weak_topics),
        unassessed_topics_count=len(unassessed_topics),
        blocking_prerequisites_count=blocking_prereqs_count,
        recommended_actions=recommended_actions,
    )

