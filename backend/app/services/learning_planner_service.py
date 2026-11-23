"""Adaptive Learning Planner Service.

Implements deterministic topic prioritization, topological prerequisite scheduling,
adaptive duration estimation, and dynamic replanning.
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import date, datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import utc_now
from app.core.planner_config import (
    BASE_DURATIONS,
    DEFAULT_BASE_DURATION,
    DEFAULT_ROLLING_DAYS,
    DURATION_ASSESSMENT_MINUTES,
    DURATION_MULTIPLIER_DEVELOPING,
    DURATION_MULTIPLIER_STRONG,
    DURATION_MULTIPLIER_WEAK_LEARN,
    DURATION_MULTIPLIER_WEAK_PRACTICE,
    FINAL_REVISION_RESERVED_DAYS,
    MAX_DAILY_STUDY_MINUTES,
    MAX_PLANNING_DAYS,
    MIN_DAILY_STUDY_MINUTES,
    MIN_SESSION_MINUTES,
    SESSION_TYPE_ASSESSMENT,
    SESSION_TYPE_LEARN,
    SESSION_TYPE_PRACTICE,
    SESSION_TYPE_REVISION,
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STATUS_PENDING,
    STATUS_SKIPPED,
    WEIGHT_EXAM_URGENCY,
    WEIGHT_GAP_SEVERITY,
    WEIGHT_PREREQUISITE_IMPACT,
    WEIGHT_TOPIC_DIFFICULTY,
    WEIGHT_TOPIC_IMPORTANCE,
)
from app.models.course import Course
from app.models.knowledge_gap import KnowledgeGapAnalysis
from app.models.plan_item import PlanItem
from app.models.study_plan import StudyPlan
from app.models.topic import Topic
from app.models.topic_prerequisite import TopicPrerequisite
from app.schemas.knowledge_gap import TopicPerformanceMetric
from app.schemas.study_plan import (
    DayScheduleGroup,
    PlanItemResponse,
    StudyPlanHistoryItem,
    StudyPlanProgress,
    StudyPlanResponseData,
)
from app.services.knowledge_gap_service import (
    build_course_prerequisite_maps,
    get_topic_performance,
)

logger = logging.getLogger(__name__)


class PlannerError(Exception):
    """Base exception for learning planner errors."""


class PlanNotFoundError(PlannerError):
    """Raised when a study plan is not found."""


class CourseEmptyError(PlannerError):
    """Raised when generating a plan for a course with no syllabus topics."""


class CourseNotFoundError(PlannerError):
    """Raised when the specified course does not exist or access is denied."""


# ---------------------------------------------------------------------------
# 1. Topic Priority Calculation
# ---------------------------------------------------------------------------


def calculate_topic_priority(
    topic: Topic,
    performance: Optional[TopicPerformanceMetric],
    dependents_count: int = 0,
    unmastered_prereqs_count: int = 0,
    days_until_exam: Optional[int] = None,
) -> float:
    """Calculate a normalized priority score (0.0 to 100.0) for a topic.

    Factors:
    - Knowledge gap severity: 35%
    - Topic importance (downstream dependents): 20%
    - Prerequisite dependency impact: 20%
    - Topic difficulty: 10%
    - Exam urgency: 15%
    """
    # 1. Knowledge Gap Severity (0 to 100)
    if performance is None or performance.knowledge_status == "not_assessed":
        gap_severity = 60.0  # Moderate-high need for diagnostic evaluation
    elif performance.knowledge_status == "weak":
        gap_severity = max(50.0, 100.0 - performance.accuracy_percentage)
    elif performance.knowledge_status == "developing":
        gap_severity = max(25.0, 100.0 - performance.accuracy_percentage)
    else:  # strong
        gap_severity = max(5.0, (100.0 - performance.accuracy_percentage) * 0.25)

    # 2. Topic Importance (0 to 100) based on downstream dependencies
    topic_importance = min(100.0, 20.0 + (dependents_count * 15.0))

    # 3. Prerequisite Dependency Impact (0 to 100)
    # If a topic has many unmastered foundational requirements, its foundational blockers must be cleared
    prereq_impact = min(100.0, unmastered_prereqs_count * 25.0)

    # 4. Topic Difficulty (0 to 100)
    diff = (topic.difficulty or "medium").lower()
    if diff in ("hard", "advanced"):
        diff_score = 90.0
    elif diff in ("easy", "beginner"):
        diff_score = 30.0
    else:
        diff_score = 60.0

    # 5. Exam Urgency (0 to 100)
    if days_until_exam is not None:
        if days_until_exam <= 0:
            exam_urgency = 100.0
        elif days_until_exam <= 7:
            exam_urgency = 95.0
        elif days_until_exam <= 14:
            exam_urgency = 80.0
        elif days_until_exam <= 30:
            exam_urgency = 60.0
        else:
            exam_urgency = max(20.0, 100.0 - (days_until_exam * 1.5))
    else:
        exam_urgency = 50.0  # Default moderate urgency for rolling schedule

    # Weighted calculation
    priority = (
        (WEIGHT_GAP_SEVERITY * gap_severity)
        + (WEIGHT_TOPIC_IMPORTANCE * topic_importance)
        + (WEIGHT_PREREQUISITE_IMPACT * prereq_impact)
        + (WEIGHT_TOPIC_DIFFICULTY * diff_score)
        + (WEIGHT_EXAM_URGENCY * exam_urgency)
    )

    return round(max(0.0, min(100.0, priority)), 2)


# ---------------------------------------------------------------------------
# 2. Prerequisite Inspection
# ---------------------------------------------------------------------------


def get_unmastered_prerequisites(
    topic_id: uuid.UUID,
    prereqs_map: Dict[uuid.UUID, List[uuid.UUID]],
    performances: Dict[uuid.UUID, TopicPerformanceMetric],
) -> List[uuid.UUID]:
    """Retrieve all direct and indirect prerequisites that are not yet strong."""
    unmastered: List[uuid.UUID] = []
    visited: Set[uuid.UUID] = set()
    queue = deque(prereqs_map.get(topic_id, []))

    while queue:
        curr_id = queue.popleft()
        if curr_id in visited:
            continue
        visited.add(curr_id)

        perf = performances.get(curr_id)
        if perf is None or perf.knowledge_status != "strong":
            unmastered.append(curr_id)

        for ancestor in prereqs_map.get(curr_id, []):
            if ancestor not in visited:
                queue.append(ancestor)

    return unmastered


# ---------------------------------------------------------------------------
# 3. Duration Estimation
# ---------------------------------------------------------------------------


def estimate_topic_duration(
    topic: Topic,
    performance: Optional[TopicPerformanceMetric],
    session_type: str,
) -> int:
    """Estimate required duration in minutes for a specific study session.

    Adaptive according to difficulty and mastery status.
    """
    diff_key = (topic.difficulty or "medium").lower()
    base = BASE_DURATIONS.get(diff_key, DEFAULT_BASE_DURATION)

    if session_type == SESSION_TYPE_ASSESSMENT:
        return DURATION_ASSESSMENT_MINUTES

    if session_type == SESSION_TYPE_REVISION:
        duration = int(base * DURATION_MULTIPLIER_STRONG)
    elif session_type == SESSION_TYPE_PRACTICE:
        duration = int(base * DURATION_MULTIPLIER_DEVELOPING)
    else:  # LEARN
        duration = int(base * DURATION_MULTIPLIER_WEAK_LEARN)

    # Enforce minimum block
    return max(MIN_SESSION_MINUTES, duration)


# ---------------------------------------------------------------------------
# 4. Topological Sort with Priority Tie-Breaking
# ---------------------------------------------------------------------------


def topological_sort_topics(
    topics: List[Topic],
    prereqs_of_topic: Dict[uuid.UUID, List[uuid.UUID]],
    dependents_of_topic: Dict[uuid.UUID, List[uuid.UUID]],
    priorities: Dict[uuid.UUID, float],
) -> List[Topic]:
    """Sort topics topologically so foundational prerequisites precede dependent topics.

    Ties at the same dependency depth are broken by priority score (highest first).
    Handles cycles gracefully via Kahn's algorithm fallback.
    """
    topic_map = {t.id: t for t in topics}
    in_degree: Dict[uuid.UUID, int] = {t.id: 0 for t in topics}

    # in-degree represents how many prerequisites topic t requires
    for t in topics:
        valid_prereqs = [p_id for p_id in prereqs_of_topic.get(t.id, []) if p_id in topic_map]
        in_degree[t.id] = len(valid_prereqs)

    # Queue contains topics ready to learn (0 unmet prerequisites)
    # We sort available nodes by priority descending
    available = [t.id for t in topics if in_degree[t.id] == 0]
    available.sort(key=lambda t_id: priorities.get(t_id, 0.0), reverse=True)

    sorted_topic_ids: List[uuid.UUID] = []

    while available:
        curr_id = available.pop(0)
        sorted_topic_ids.append(curr_id)

        # For all topics that depend on curr_id, decrement their in-degree
        dependents = [d_id for d_id in dependents_of_topic.get(curr_id, []) if d_id in topic_map]
        for dep_id in dependents:
            in_degree[dep_id] -= 1
            if in_degree[dep_id] == 0:
                available.append(dep_id)

        # Re-sort available pool so higher priority topics are scheduled earlier
        available.sort(key=lambda t_id: priorities.get(t_id, 0.0), reverse=True)

    # If cyclic dependencies exist, append any remaining unprocessed topics by priority
    if len(sorted_topic_ids) < len(topics):
        remaining = [t.id for t in topics if t.id not in sorted_topic_ids]
        remaining.sort(key=lambda t_id: priorities.get(t_id, 0.0), reverse=True)
        sorted_topic_ids.extend(remaining)

    return [topic_map[t_id] for t_id in sorted_topic_ids]


# ---------------------------------------------------------------------------
# 5. Study Plan Scheduling Logic
# ---------------------------------------------------------------------------


class ScheduledSessionItem:
    """Internal representation of a session before DB persistence."""

    def __init__(
        self,
        topic: Topic,
        session_type: str,
        duration_minutes: int,
        priority_score: float,
        scheduled_date: date,
        sequence_number: int,
    ):
        self.topic = topic
        self.session_type = session_type
        self.duration_minutes = duration_minutes
        self.priority_score = priority_score
        self.scheduled_date = scheduled_date
        self.sequence_number = sequence_number


def schedule_topics(
    ordered_topics: List[Topic],
    performances: Dict[uuid.UUID, TopicPerformanceMetric],
    priorities: Dict[uuid.UUID, float],
    daily_minutes: int,
    exam_date: Optional[date] = None,
    start_date: Optional[date] = None,
) -> Tuple[List[ScheduledSessionItem], List[Topic]]:
    """Schedule study sessions across calendar days respecting daily study budgets.

    Returns:
        (scheduled_items, unslotted_topics)
    """
    if start_date is None:
        start_date = date.today()

    daily_budget = max(MIN_DAILY_STUDY_MINUTES, min(MAX_DAILY_STUDY_MINUTES, daily_minutes))

    # Calculate deadline window
    if exam_date is not None and exam_date > start_date:
        total_available_days = (exam_date - start_date).days
        # Reserve final 1-2 days exclusively for final revision before exam if window permits
        if total_available_days > FINAL_REVISION_RESERVED_DAYS:
            effective_study_days = total_available_days - FINAL_REVISION_RESERVED_DAYS
            final_revision_start = start_date + timedelta(days=effective_study_days)
        else:
            effective_study_days = max(1, total_available_days - 1)
            final_revision_start = None
    else:
        # Rolling 7-day plan
        effective_study_days = DEFAULT_ROLLING_DAYS
        final_revision_start = None

    # Generate needed session descriptors for each topic in order
    pending_sessions: List[Tuple[Topic, str, int, float]] = []

    for topic in ordered_topics:
        perf = performances.get(topic.id)
        priority = priorities.get(topic.id, 50.0)

        if perf is None or perf.knowledge_status == "not_assessed":
            # Schedule diagnostic assessment first
            dur = estimate_topic_duration(topic, perf, SESSION_TYPE_ASSESSMENT)
            pending_sessions.append((topic, SESSION_TYPE_ASSESSMENT, dur, priority))
        elif perf.knowledge_status == "weak":
            # Weak topics get concept learning session followed by practice
            learn_dur = estimate_topic_duration(topic, perf, SESSION_TYPE_LEARN)
            practice_dur = estimate_topic_duration(topic, perf, SESSION_TYPE_PRACTICE)
            pending_sessions.append((topic, SESSION_TYPE_LEARN, learn_dur, priority))
            pending_sessions.append((topic, SESSION_TYPE_PRACTICE, practice_dur, priority * 0.95))
        elif perf.knowledge_status == "developing":
            # Developing topics get focused practice
            practice_dur = estimate_topic_duration(topic, perf, SESSION_TYPE_PRACTICE)
            pending_sessions.append((topic, SESSION_TYPE_PRACTICE, practice_dur, priority))
        else:
            # Strong topics get light revision
            rev_dur = estimate_topic_duration(topic, perf, SESSION_TYPE_REVISION)
            pending_sessions.append((topic, SESSION_TYPE_REVISION, rev_dur, priority))

    # Distribute sessions across calendar days respecting daily_budget
    scheduled: List[ScheduledSessionItem] = []
    unslotted_topics: Set[Topic] = set()

    current_day_offset = 0
    current_day_used = 0
    seq = 1

    for topic, s_type, dur, priority in pending_sessions:
        # Check if we still have available days before exam / within window
        if current_day_offset >= effective_study_days:
            unslotted_topics.add(topic)
            continue

        # If adding this session exceeds daily budget on current day, advance to next day
        if current_day_used + dur > daily_budget and current_day_used > 0:
            current_day_offset += 1
            current_day_used = 0

            # Re-check boundary
            if current_day_offset >= effective_study_days:
                unslotted_topics.add(topic)
                continue

        target_date = start_date + timedelta(days=current_day_offset)

        scheduled.append(
            ScheduledSessionItem(
                topic=topic,
                session_type=s_type,
                duration_minutes=dur,
                priority_score=priority,
                scheduled_date=target_date,
                sequence_number=seq,
            )
        )
        current_day_used += dur
        seq += 1

    # If exam date has reserved final revision window, schedule final wrap-up sessions
    if final_revision_start is not None and scheduled:
        # Pick top 2 most critical or weak topics for final exam polish
        critical_topics = [
            t for t in ordered_topics
            if performances.get(t.id) and performances[t.id].knowledge_status in ("weak", "developing")
        ]
        if not critical_topics:
            critical_topics = ordered_topics[:2]

        for i, rev_topic in enumerate(critical_topics[:2]):
            rev_date = final_revision_start + timedelta(days=min(i, FINAL_REVISION_RESERVED_DAYS - 1))
            rev_dur = min(daily_budget, estimate_topic_duration(rev_topic, performances.get(rev_topic.id), SESSION_TYPE_REVISION))
            scheduled.append(
                ScheduledSessionItem(
                    topic=rev_topic,
                    session_type=SESSION_TYPE_REVISION,
                    duration_minutes=rev_dur,
                    priority_score=99.0,
                    scheduled_date=rev_date,
                    sequence_number=seq,
                )
            )
            seq += 1

    return scheduled, list(unslotted_topics)


# ---------------------------------------------------------------------------
# 6. Full Plan Generation Pipeline
# ---------------------------------------------------------------------------


def generate_learning_plan(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
    exam_date: Optional[date] = None,
    daily_minutes: Optional[int] = None,
    force_regenerate: bool = False,
) -> StudyPlanResponseData:
    """Generate a personalized, prerequisite-respecting adaptive study plan.

    Archiving any existing active plans into historical versions.
    """
    # 1. Verify course ownership
    course = db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user_id)
    ).scalar_one_or_none()

    if not course:
        raise CourseNotFoundError(f"Course {course_id} not found or access denied.")

    # Resolve daily_minutes and exam_date fallback
    effective_daily_minutes = daily_minutes or course.daily_minutes or 60
    effective_exam_date = exam_date if exam_date is not None else course.exam_date

    # 2. Check for syllabus topics
    topics = list(
        db.execute(
            select(Topic)
            .where(Topic.course_id == course_id)
            .order_by(Topic.created_at, Topic.name)
        ).scalars().all()
    )

    if not topics:
        raise CourseEmptyError("Cannot generate a study plan for a course with no syllabus topics.")

    # 3. Retrieve Topic Performance & Prerequisite Graph
    performances = get_topic_performance(db, user_id, course_id)
    prereqs_of_topic, dependents_of_topic = build_course_prerequisite_maps(db, course_id)

    # 4. Calculate Topic Priorities
    priorities: Dict[uuid.UUID, float] = {}
    today = date.today()
    days_to_exam = (effective_exam_date - today).days if effective_exam_date and effective_exam_date > today else None

    for t in topics:
        perf = performances.get(t.id)
        dep_count = len(dependents_of_topic.get(t.id, []))
        unmastered_prereqs = get_unmastered_prerequisites(t.id, prereqs_of_topic, performances)
        priorities[t.id] = calculate_topic_priority(
            topic=t,
            performance=perf,
            dependents_count=dep_count,
            unmastered_prereqs_count=len(unmastered_prereqs),
            days_until_exam=days_to_exam,
        )

    # 5. Order Topics Topologically (prerequisites scheduled before dependent topics)
    ordered_topics = topological_sort_topics(
        topics=topics,
        prereqs_of_topic=prereqs_of_topic,
        dependents_of_topic=dependents_of_topic,
        priorities=priorities,
    )

    # 6. Schedule Sessions
    scheduled_sessions, unslotted = schedule_topics(
        ordered_topics=ordered_topics,
        performances=performances,
        priorities=priorities,
        daily_minutes=effective_daily_minutes,
        exam_date=effective_exam_date,
        start_date=today,
    )

    # 7. Version Management: Archive existing active plans
    existing_plans = list(
        db.execute(
            select(StudyPlan)
            .where(StudyPlan.course_id == course_id, StudyPlan.user_id == user_id)
            .order_by(desc(StudyPlan.version))
        ).scalars().all()
    )

    max_version = 0
    for p in existing_plans:
        max_version = max(max_version, p.version)
        if p.status == "active":
            p.status = "archived"

    new_version = max_version + 1

    # 8. Create new StudyPlan
    summary_text = (
        f"Generated plan v{new_version} covering {len(scheduled_sessions)} sessions across "
        f"{len(set(s.scheduled_date for s in scheduled_sessions))} days at {effective_daily_minutes} mins/day."
    )
    if unslotted:
        summary_text += f" ({len(unslotted)} topic(s) unslotted due to exam horizon limits)."

    new_plan = StudyPlan(
        user_id=user_id,
        course_id=course_id,
        version=new_version,
        status="active",
        daily_minutes=effective_daily_minutes,
        exam_date=effective_exam_date,
        summary=summary_text,
    )
    db.add(new_plan)
    db.flush()

    # 9. Create PlanItems
    db_items: List[PlanItem] = []
    for item in scheduled_sessions:
        p_item = PlanItem(
            plan_id=new_plan.id,
            topic_id=item.topic.id,
            scheduled_date=item.scheduled_date,
            duration_minutes=item.duration_minutes,
            priority=max(1, int(round(item.priority_score / 10))),
            priority_score=item.priority_score,
            session_type=item.session_type,
            status=STATUS_PENDING,
            sequence_number=item.sequence_number,
        )
        db_items.append(p_item)

    db.add_all(db_items)
    db.commit()

    return _build_plan_response(
        db=db,
        plan=new_plan,
        items=db_items,
        course=course,
        topics=topics,
        performances=performances,
        prereqs_map=prereqs_of_topic,
        unslotted=unslotted,
    )


# ---------------------------------------------------------------------------
# 7. Adaptive Replanning & Rebalance
# ---------------------------------------------------------------------------


def rebalance_learning_plan(
    db: Session,
    user_id: uuid.UUID,
    plan_id: uuid.UUID,
    updated_daily_minutes: Optional[int] = None,
    updated_exam_date: Optional[date] = None,
) -> StudyPlanResponseData:
    """Dynamically rebalance an active study plan.

    Preserves completed items, adapts remaining schedule to current date & mastery.
    """
    plan = db.execute(
        select(StudyPlan)
        .options(selectinload(StudyPlan.items).selectinload(PlanItem.topic))
        .where(StudyPlan.id == plan_id, StudyPlan.user_id == user_id)
    ).scalar_one_or_none()

    if not plan:
        raise PlanNotFoundError(f"Study plan {plan_id} not found.")

    course = db.execute(
        select(Course).where(Course.id == plan.course_id, Course.user_id == user_id)
    ).scalar_one_or_none()

    if not course:
        raise CourseNotFoundError("Associated course not found.")

    if updated_daily_minutes is not None:
        plan.daily_minutes = updated_daily_minutes
    if updated_exam_date is not None:
        plan.exam_date = updated_exam_date

    today = date.today()
    items = sorted(plan.items, key=lambda i: i.sequence_number)

    completed_items = [i for i in items if i.status == STATUS_COMPLETED]
    remaining_items = [i for i in items if i.status != STATUS_COMPLETED]

    # Re-evaluate topic performances
    performances = get_topic_performance(db, user_id, course.id)
    prereqs_of_topic, dependents_of_topic = build_course_prerequisite_maps(db, course.id)

    # Rebalance remaining sessions starting from today forward
    current_date = today
    current_day_used = 0
    daily_budget = plan.daily_minutes or course.daily_minutes or 60

    for item in remaining_items:
        # Check if topic has become strong in the meantime -> adapt to revision
        perf = performances.get(item.topic_id)
        if perf and perf.knowledge_status == "strong" and item.session_type == SESSION_TYPE_LEARN:
            item.session_type = SESSION_TYPE_REVISION
            item.duration_minutes = estimate_topic_duration(item.topic, perf, SESSION_TYPE_REVISION)

        dur = item.duration_minutes

        if current_day_used + dur > daily_budget and current_day_used > 0:
            current_date += timedelta(days=1)
            current_day_used = 0

        item.scheduled_date = current_date
        current_day_used += dur

    db.commit()

    topics = list(
        db.execute(select(Topic).where(Topic.course_id == course.id)).scalars().all()
    )

    return _build_plan_response(
        db=db,
        plan=plan,
        items=items,
        course=course,
        topics=topics,
        performances=performances,
        prereqs_map=prereqs_of_topic,
        unslotted=[],
    )


# ---------------------------------------------------------------------------
# 8. Query Functions
# ---------------------------------------------------------------------------


def get_active_study_plan(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
) -> Optional[StudyPlanResponseData]:
    """Retrieve the current active study plan for a user's course."""
    course = db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user_id)
    ).scalar_one_or_none()

    if not course:
        raise CourseNotFoundError(f"Course {course_id} not found.")

    plan = db.execute(
        select(StudyPlan)
        .options(selectinload(StudyPlan.items).selectinload(PlanItem.topic))
        .where(
            StudyPlan.course_id == course_id,
            StudyPlan.user_id == user_id,
            StudyPlan.status == "active",
        )
        .order_by(desc(StudyPlan.version))
    ).scalars().first()

    if not plan:
        return None

    topics = list(
        db.execute(select(Topic).where(Topic.course_id == course_id)).scalars().all()
    )
    performances = get_topic_performance(db, user_id, course_id)
    prereqs_map, _ = build_course_prerequisite_maps(db, course_id)

    return _build_plan_response(
        db=db,
        plan=plan,
        items=plan.items,
        course=course,
        topics=topics,
        performances=performances,
        prereqs_map=prereqs_map,
        unslotted=[],
    )


def get_study_plan_by_id(
    db: Session,
    user_id: uuid.UUID,
    plan_id: uuid.UUID,
) -> StudyPlanResponseData:
    """Retrieve a specific study plan version by ID."""
    plan = db.execute(
        select(StudyPlan)
        .options(selectinload(StudyPlan.items).selectinload(PlanItem.topic))
        .where(StudyPlan.id == plan_id, StudyPlan.user_id == user_id)
    ).scalar_one_or_none()

    if not plan:
        raise PlanNotFoundError(f"Study plan {plan_id} not found.")

    course = db.execute(
        select(Course).where(Course.id == plan.course_id, Course.user_id == user_id)
    ).scalar_one_or_none()

    topics = list(
        db.execute(select(Topic).where(Topic.course_id == plan.course_id)).scalars().all()
    )
    performances = get_topic_performance(db, user_id, plan.course_id)
    prereqs_map, _ = build_course_prerequisite_maps(db, plan.course_id)

    return _build_plan_response(
        db=db,
        plan=plan,
        items=plan.items,
        course=course,
        topics=topics,
        performances=performances,
        prereqs_map=prereqs_map,
        unslotted=[],
    )


def update_plan_item_status(
    db: Session,
    user_id: uuid.UUID,
    plan_id: uuid.UUID,
    item_id: uuid.UUID,
    new_status: Optional[str] = None,
    new_duration: Optional[int] = None,
    new_date: Optional[date] = None,
) -> PlanItemResponse:
    """Update progress status (PENDING, IN_PROGRESS, COMPLETED, SKIPPED) of a plan session."""
    plan = db.execute(
        select(StudyPlan).where(StudyPlan.id == plan_id, StudyPlan.user_id == user_id)
    ).scalar_one_or_none()

    if not plan:
        raise PlanNotFoundError(f"Study plan {plan_id} not found.")

    item = db.execute(
        select(PlanItem)
        .options(selectinload(PlanItem.topic))
        .where(PlanItem.id == item_id, PlanItem.plan_id == plan_id)
    ).scalar_one_or_none()

    if not item:
        raise PlanNotFoundError(f"Plan item {item_id} not found.")

    if new_status:
        normalized_status = new_status.upper()
        item.status = normalized_status
        if normalized_status == STATUS_COMPLETED:
            item.completed_at = utc_now()
        else:
            item.completed_at = None

    if new_duration is not None:
        item.duration_minutes = new_duration

    if new_date is not None:
        item.scheduled_date = new_date

    db.commit()
    db.refresh(item)

    return PlanItemResponse(
        id=item.id,
        plan_id=item.plan_id,
        topic_id=item.topic_id,
        topic_name=item.topic.name if item.topic else "Topic",
        unit_name=item.topic.unit_name if item.topic else None,
        difficulty=item.topic.difficulty if item.topic else "medium",
        scheduled_date=item.scheduled_date,
        duration_minutes=item.duration_minutes,
        priority_score=item.priority_score,
        session_type=item.session_type,
        status=item.status,
        sequence_number=item.sequence_number,
        created_at=item.created_at,
        completed_at=item.completed_at,
        is_prerequisite_satisfied=True,
        unmet_prerequisites=[],
    )


def get_study_plan_history(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
) -> List[StudyPlanHistoryItem]:
    """Retrieve history of all study plans generated for this course."""
    course = db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user_id)
    ).scalar_one_or_none()

    if not course:
        raise CourseNotFoundError(f"Course {course_id} not found.")

    plans = list(
        db.execute(
            select(StudyPlan)
            .options(selectinload(StudyPlan.items))
            .where(StudyPlan.course_id == course_id, StudyPlan.user_id == user_id)
            .order_by(desc(StudyPlan.version))
        ).scalars().all()
    )

    history: List[StudyPlanHistoryItem] = []
    for p in plans:
        total = len(p.items)
        comp = sum(1 for i in p.items if i.status == STATUS_COMPLETED)
        pct = round((comp / total) * 100.0, 1) if total > 0 else 0.0

        history.append(
            StudyPlanHistoryItem(
                id=p.id,
                course_id=p.course_id,
                version=p.version,
                status=p.status,
                created_at=p.created_at,
                exam_date=p.exam_date,
                daily_minutes=p.daily_minutes,
                total_items=total,
                completed_items=comp,
                completion_percentage=pct,
            )
        )

    return history


# ---------------------------------------------------------------------------
# 9. Internal Response Formatter & Progress Calculator
# ---------------------------------------------------------------------------


def _build_plan_response(
    db: Session,
    plan: StudyPlan,
    items: List[PlanItem],
    course: Optional[Course],
    topics: List[Topic],
    performances: Dict[uuid.UUID, TopicPerformanceMetric],
    prereqs_map: Dict[uuid.UUID, List[uuid.UUID]],
    unslotted: List[Topic],
) -> StudyPlanResponseData:
    """Group items by calendar date and build comprehensive response."""
    topic_map = {t.id: t for t in topics}

    # Track which topics are satisfied/completed in the plan so far
    completed_topic_ids = set(
        i.topic_id for i in items if i.status == STATUS_COMPLETED
    )

    # Also topics that were assessed as strong initially are satisfied
    for t_id, perf in performances.items():
        if perf.knowledge_status == "strong":
            completed_topic_ids.add(t_id)

    # Build PlanItemResponses
    item_responses: List[PlanItemResponse] = []
    items_by_date: Dict[date, List[PlanItemResponse]] = defaultdict(list)

    for item in sorted(items, key=lambda i: (i.scheduled_date, i.sequence_number)):
        t = topic_map.get(item.topic_id)
        t_name = t.name if t else "Topic"
        u_name = t.unit_name if t else None
        diff = t.difficulty if t else "medium"

        # Check prerequisite satisfaction
        all_prereqs = prereqs_map.get(item.topic_id, [])
        unmet_names: List[str] = []
        for p_id in all_prereqs:
            if p_id not in completed_topic_ids:
                p_topic = topic_map.get(p_id)
                if p_topic:
                    unmet_names.append(p_topic.name)

        is_satisfied = len(unmet_names) == 0

        p_resp = PlanItemResponse(
            id=item.id,
            plan_id=item.plan_id,
            topic_id=item.topic_id,
            topic_name=t_name,
            unit_name=u_name,
            difficulty=diff,
            scheduled_date=item.scheduled_date,
            duration_minutes=item.duration_minutes,
            priority_score=item.priority_score,
            session_type=item.session_type,
            status=item.status,
            sequence_number=item.sequence_number,
            created_at=item.created_at,
            completed_at=item.completed_at,
            is_prerequisite_satisfied=is_satisfied,
            unmet_prerequisites=unmet_names,
        )
        item_responses.append(p_resp)
        items_by_date[item.scheduled_date].append(p_resp)

    # Build DayScheduleGroups
    days: List[DayScheduleGroup] = []
    sorted_dates = sorted(items_by_date.keys())
    day_num = 1

    for d in sorted_dates:
        day_sessions = items_by_date[d]
        total_mins = sum(s.duration_minutes for s in day_sessions)
        is_exam = plan.exam_date is not None and d == plan.exam_date
        is_final_rev = any(s.session_type == SESSION_TYPE_REVISION and s.priority_score >= 90.0 for s in day_sessions)

        days.append(
            DayScheduleGroup(
                date=d,
                day_number=day_num,
                total_minutes=total_mins,
                is_exam_day=is_exam,
                is_final_revision_day=is_final_rev,
                sessions=day_sessions,
            )
        )
        day_num += 1

    # Progress calculations
    total_count = len(items)
    comp_count = sum(1 for i in items if i.status == STATUS_COMPLETED)
    inp_count = sum(1 for i in items if i.status == STATUS_IN_PROGRESS)
    skip_count = sum(1 for i in items if i.status == STATUS_SKIPPED)
    pend_count = sum(1 for i in items if i.status == STATUS_PENDING)

    comp_pct = round((comp_count / total_count) * 100.0, 1) if total_count > 0 else 0.0
    tot_mins = sum(i.duration_minutes for i in items)
    comp_mins = sum(i.duration_minutes for i in items if i.status == STATUS_COMPLETED)

    today = date.today()
    days_rem = (plan.exam_date - today).days if plan.exam_date and plan.exam_date >= today else None

    # On track calculation: are past sessions mostly completed?
    overdue_count = sum(
        1 for i in items if i.scheduled_date < today and i.status not in (STATUS_COMPLETED, STATUS_SKIPPED)
    )
    is_on_track = overdue_count == 0

    progress = StudyPlanProgress(
        total_items=total_count,
        completed_items=comp_count,
        in_progress_items=inp_count,
        pending_items=pend_count,
        skipped_items=skip_count,
        completion_percentage=comp_pct,
        total_minutes_scheduled=tot_mins,
        completed_minutes=comp_mins,
        days_remaining=days_rem,
        target_exam_date=plan.exam_date,
        daily_minutes_target=plan.daily_minutes,
        unslotted_topics_count=len(unslotted),
        unslotted_topic_names=[t.name for t in unslotted],
        is_on_track=is_on_track,
    )

    return StudyPlanResponseData(
        id=plan.id,
        course_id=plan.course_id,
        course_title=course.title if course else "Course",
        version=plan.version,
        status=plan.status,
        created_at=plan.created_at,
        exam_date=plan.exam_date,
        daily_minutes=plan.daily_minutes,
        summary=plan.summary,
        progress=progress,
        days=days,
    )
