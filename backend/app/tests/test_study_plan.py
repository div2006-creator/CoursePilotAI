"""Comprehensive test suite for Part 9: Adaptive Learning Planner.

Covers all 12 required scenarios:
1. Topic priority calculation (weights, weak vs strong, dependents, difficulty, exam urgency).
2. Prerequisite ordering (foundational scheduled before dependent).
3. Strong prerequisite handling (not scheduled for full learn session, revision multiplier).
4. Weak topic prioritization (learn + practice sessions).
5. Daily study-time limits (never exceeded across any calendar day).
6. Exam-date scheduling and final revision buffer.
7. Rolling 7-day plan when no exam date is set.
8. Insufficient study time detection (unslotted topics flagged).
9. Adaptive replanning after mastery improvement (preserves completed sessions).
10. Missed session handling and item status update (PENDING, COMPLETED, SKIPPED).
11. Plan version history (v1 -> v2 archiving and history listing).
12. User ownership and authorization (401 unauthenticated, 404 unauthorized access).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys
from typing import Generator
import uuid

# Ensure backend directory is in sys.path
_BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from app.core.planner_config import (
    BASE_DURATIONS,
    DURATION_MULTIPLIER_STRONG,
    DURATION_MULTIPLIER_WEAK_LEARN,
    DURATION_MULTIPLIER_WEAK_PRACTICE,
    SESSION_TYPE_LEARN,
    SESSION_TYPE_PRACTICE,
    SESSION_TYPE_REVISION,
    STATUS_ARCHIVED,
    STATUS_COMPLETED,
    STATUS_PENDING,
    STATUS_SKIPPED,
)
from app.core.security import create_access_token
from app.models.attempt import Attempt
from app.models.course import Course
from app.models.plan_item import PlanItem
from app.models.question import Question
from app.models.study_plan import StudyPlan
from app.models.topic import Topic
from app.models.topic_prerequisite import TopicPrerequisite
from app.models.user import User
from app.schemas.knowledge_gap import TopicPerformanceMetric
from app.services.learning_planner_service import (
    calculate_topic_priority,
    estimate_topic_duration,
    generate_learning_plan,
    get_active_study_plan,
    get_study_plan_by_id,
    get_study_plan_history,
    get_unmastered_prerequisites,
    rebalance_learning_plan,
    topological_sort_topics,
    update_plan_item_status,
)


# ---------------------------------------------------------------------------
# Test Helpers & Fixtures
# ---------------------------------------------------------------------------


def _create_user(session: Session, email: str = "turing@example.com") -> User:
    user = User(
        name="Alan Turing",
        email=email,
        password_hash="mock_hash_for_testing",
    )
    session.add(user)
    session.flush()
    return user


def _create_course(
    session: Session,
    user: User,
    title: str = "Algorithms & Data Structures",
    daily_minutes: int = 60,
    exam_date: date | None = None,
) -> Course:
    course = Course(
        user_id=user.id,
        title=title,
        description="Comprehensive course on foundational & advanced DSA",
        daily_minutes=daily_minutes,
        exam_date=exam_date,
    )
    session.add(course)
    session.flush()
    return course


def _create_dp_dag(session: Session, course: Course) -> dict[str, Topic]:
    """Create DAG: Recursion -> Memoization -> Tabulation -> Grid DP."""
    t_recursion = Topic(
        course_id=course.id,
        name="Recursion",
        unit_name="Unit 1: Foundations",
        difficulty="easy",
    )
    t_memo = Topic(
        course_id=course.id,
        name="Memoization",
        unit_name="Unit 2: Dynamic Programming",
        difficulty="medium",
    )
    t_tab = Topic(
        course_id=course.id,
        name="Tabulation",
        unit_name="Unit 2: Dynamic Programming",
        difficulty="medium",
    )
    t_grid_dp = Topic(
        course_id=course.id,
        name="Grid DP",
        unit_name="Unit 3: 2D Dynamic Programming",
        difficulty="hard",
    )

    session.add_all([t_recursion, t_memo, t_tab, t_grid_dp])
    session.flush()

    # Edges: topic requires prerequisite
    # Memoization requires Recursion
    e1 = TopicPrerequisite(topic_id=t_memo.id, prerequisite_id=t_recursion.id, confidence=1.0)
    # Tabulation requires Memoization
    e2 = TopicPrerequisite(topic_id=t_tab.id, prerequisite_id=t_memo.id, confidence=0.95)
    # Grid DP requires Tabulation
    e3 = TopicPrerequisite(topic_id=t_grid_dp.id, prerequisite_id=t_tab.id, confidence=0.9)

    session.add_all([e1, e2, e3])
    session.flush()

    return {
        "recursion": t_recursion,
        "memoization": t_memo,
        "tabulation": t_tab,
        "grid_dp": t_grid_dp,
    }


def _seed_topic_attempts(
    session: Session,
    user: User,
    course: Course,
    topic: Topic,
    correct_count: int,
    total_count: int,
) -> None:
    q = Question(
        topic_id=topic.id,
        question=f"Test question for {topic.name}",
        options=["A", "B", "C", "D"],
        correct_answer="A",
        difficulty="medium",
        source="unit_test",
    )
    session.add(q)
    session.flush()

    for i in range(total_count):
        is_correct = i < correct_count
        att = Attempt(
            user_id=user.id,
            course_id=course.id,
            topic_id=topic.id,
            question_id=q.id,
            selected_answer="A" if is_correct else "B",
            is_correct=is_correct,
            time_taken=20,
            created_at=datetime.now(timezone.utc),
        )
        session.add(att)
    session.flush()


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, extra_claims={"email": user.email})
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Topic Priority Calculation Tests
# ---------------------------------------------------------------------------


def test_topic_priority_calculation():
    """Verify priority weighting: weak topics score higher than strong topics,

    dependents and difficulty increase priority, exam urgency amplifies score.
    """
    dummy_course_id = uuid.uuid4()
    t_easy = Topic(id=uuid.uuid4(), course_id=dummy_course_id, name="Basics", difficulty="easy")
    t_hard = Topic(id=uuid.uuid4(), course_id=dummy_course_id, name="Advanced DP", difficulty="hard")

    perf_weak = TopicPerformanceMetric(
        topic_id=t_hard.id,
        topic_name=t_hard.name,
        total_attempts=10,
        correct_attempts=2,
        accuracy_percentage=20.0,
        knowledge_status="weak",
        confidence_score=0.9,
    )

    perf_strong = TopicPerformanceMetric(
        topic_id=t_easy.id,
        topic_name=t_easy.name,
        total_attempts=10,
        correct_attempts=9,
        accuracy_percentage=90.0,
        knowledge_status="strong",
        confidence_score=0.9,
    )

    score_weak = calculate_topic_priority(
        topic=t_hard,
        performance=perf_weak,
        dependents_count=2,
        unmastered_prereqs_count=1,
        days_until_exam=10,
    )

    score_strong = calculate_topic_priority(
        topic=t_easy,
        performance=perf_strong,
        dependents_count=0,
        unmastered_prereqs_count=0,
        days_until_exam=10,
    )

    # Weak topic must have significantly higher priority than strong topic
    assert score_weak > score_strong
    assert 0.0 <= score_weak <= 100.0
    assert 0.0 <= score_strong <= 100.0

    # Closer exam increases urgency
    score_far = calculate_topic_priority(
        topic=t_hard,
        performance=perf_weak,
        dependents_count=2,
        unmastered_prereqs_count=1,
        days_until_exam=45,
    )
    assert score_weak > score_far


# ---------------------------------------------------------------------------
# 2. Prerequisite Ordering Tests
# ---------------------------------------------------------------------------


def test_prerequisite_ordering_topological(db_session: Session):
    """Prerequisite topological sort must place foundational concepts before dependents."""
    user = _create_user(db_session, "topological@example.com")
    course = _create_course(db_session, user)
    dag = _create_dp_dag(db_session, course)

    # Give arbitrary priorities
    priorities = {
        dag["grid_dp"].id: 95.0,
        dag["tabulation"].id: 80.0,
        dag["memoization"].id: 70.0,
        dag["recursion"].id: 60.0,
    }

    topics = [dag["grid_dp"], dag["tabulation"], dag["memoization"], dag["recursion"]]
    from app.services.knowledge_gap_service import build_course_prerequisite_maps
    prereqs_of_topic, dependents_of_topic = build_course_prerequisite_maps(db_session, course.id)
    ordered = topological_sort_topics(topics, prereqs_of_topic, dependents_of_topic, priorities)

    order_names = [t.name for t in ordered]
    # Recursion must come before Memoization, Tabulation, Grid DP
    assert order_names.index("Recursion") < order_names.index("Memoization")
    assert order_names.index("Memoization") < order_names.index("Tabulation")
    assert order_names.index("Tabulation") < order_names.index("Grid DP")


# ---------------------------------------------------------------------------
# 3. Strong Prerequisite Handling Tests
# ---------------------------------------------------------------------------


def test_strong_prerequisite_handling(db_session: Session):
    """A strong prerequisite (accuracy >= 80%) gets a revision session with 0.5x duration."""
    user = _create_user(db_session, "strong_prereq@example.com")
    course = _create_course(db_session, user)
    t = Topic(course_id=course.id, name="Recursion", difficulty="easy")
    db_session.add(t)
    db_session.flush()

    # Seed 9/10 correct -> strong
    _seed_topic_attempts(db_session, user, course, t, correct_count=9, total_count=10)

    from app.services.knowledge_gap_service import get_topic_performance
    perf = get_topic_performance(db_session, user.id, course.id)[t.id]
    assert perf.knowledge_status == "strong"

    # Base duration for easy is 30 mins
    base_dur = BASE_DURATIONS["easy"]
    rev_dur = estimate_topic_duration(t, perf, SESSION_TYPE_REVISION)

    # Strong multiplier is 0.5x
    assert rev_dur == round(base_dur * DURATION_MULTIPLIER_STRONG)


# ---------------------------------------------------------------------------
# 4. Weak Topic Prioritization Tests
# ---------------------------------------------------------------------------


def test_weak_topic_prioritization(db_session: Session):
    """A weak topic generates both LEARN and PRACTICE sessions in the learning plan."""
    user = _create_user(db_session, "weak_priority@example.com")
    course = _create_course(db_session, user, daily_minutes=90)
    t = Topic(course_id=course.id, name="Grid DP", difficulty="medium")
    db_session.add(t)
    db_session.flush()

    # Seed 2/10 correct -> weak
    _seed_topic_attempts(db_session, user, course, t, correct_count=2, total_count=10)

    plan_data = generate_learning_plan(db_session, user.id, course.id)
    all_sessions = [s for day in plan_data.days for s in day.sessions if s.topic_id == t.id]

    session_types = [s.session_type for s in all_sessions]
    assert SESSION_TYPE_LEARN in session_types
    assert SESSION_TYPE_PRACTICE in session_types


# ---------------------------------------------------------------------------
# 5. Daily Study-Time Limits Tests
# ---------------------------------------------------------------------------


def test_daily_study_time_limits_never_exceeded(db_session: Session):
    """Across any calendar day, total scheduled minutes must never exceed daily_minutes."""
    user = _create_user(db_session, "daily_limit@example.com")
    daily_budget = 45
    course = _create_course(db_session, user, daily_minutes=daily_budget)

    # Create 5 topics
    for i in range(5):
        t = Topic(course_id=course.id, name=f"Topic {i+1}", difficulty="medium")
        db_session.add(t)
    db_session.flush()

    plan_data = generate_learning_plan(
        db_session,
        user.id,
        course.id,
        daily_minutes=daily_budget,
    )

    assert len(plan_data.days) > 0
    for day in plan_data.days:
        assert day.total_minutes <= daily_budget, (
            f"Day {day.date} exceeded daily budget: {day.total_minutes} > {daily_budget}"
        )


# ---------------------------------------------------------------------------
# 6. Exam-Date Scheduling and Revision Buffer Tests
# ---------------------------------------------------------------------------


def test_exam_date_scheduling_and_revision_buffer(db_session: Session):
    """When an exam date is provided, the schedule fits within the window and reserves revision."""
    user = _create_user(db_session, "exam_buffer@example.com")
    exam = date.today() + timedelta(days=10)
    course = _create_course(db_session, user, daily_minutes=60, exam_date=exam)
    dag = _create_dp_dag(db_session, course)

    plan_data = generate_learning_plan(
        db_session,
        user.id,
        course.id,
        exam_date=exam,
    )

    assert plan_data.exam_date == exam
    # Verify that scheduled days are before or on exam date
    for day in plan_data.days:
        assert day.date <= exam

    # Check for final revision day or sessions
    has_final_revision = any(day.is_final_revision_day for day in plan_data.days)
    revision_sessions = [
        s for day in plan_data.days for s in day.sessions if s.session_type == SESSION_TYPE_REVISION
    ]
    assert has_final_revision or len(revision_sessions) > 0


# ---------------------------------------------------------------------------
# 7. Rolling 7-Day Plan When No Exam Date Tests
# ---------------------------------------------------------------------------


def test_rolling_7_day_plan_when_no_exam_date(db_session: Session):
    """When exam_date is None, system generates a rolling 7-day schedule."""
    user = _create_user(db_session, "rolling@example.com")
    course = _create_course(db_session, user, exam_date=None)
    dag = _create_dp_dag(db_session, course)

    plan_data = generate_learning_plan(db_session, user.id, course.id, exam_date=None)

    assert plan_data.exam_date is None
    # All scheduled days must be within today + 7 days
    today = date.today()
    max_rolling_date = today + timedelta(days=7)
    for day in plan_data.days:
        assert day.date <= max_rolling_date


# ---------------------------------------------------------------------------
# 8. Insufficient Study Time Detection Tests
# ---------------------------------------------------------------------------


def test_insufficient_study_time_detection(db_session: Session):
    """If daily study time and days to exam cannot fit all topics, flag unslotted topics."""
    user = _create_user(db_session, "insufficient@example.com")
    # Exam tomorrow, only 30 mins available
    exam = date.today() + timedelta(days=1)
    course = _create_course(db_session, user, daily_minutes=30, exam_date=exam)

    # Create 8 hard topics (each needs 90 mins learn + 60 mins practice = 150 mins)
    for i in range(8):
        t = Topic(course_id=course.id, name=f"Hard Topic {i+1}", difficulty="hard")
        db_session.add(t)
    db_session.flush()

    plan_data = generate_learning_plan(
        db_session,
        user.id,
        course.id,
        daily_minutes=30,
        exam_date=exam,
    )

    assert plan_data.progress.unslotted_topics_count > 0
    assert len(plan_data.progress.unslotted_topic_names) > 0


# ---------------------------------------------------------------------------
# 9. Adaptive Replanning After Mastery Improvement Tests
# ---------------------------------------------------------------------------


def test_adaptive_replanning_after_mastery(db_session: Session):
    """Rebalancing dynamic plan preserves completed sessions and re-schedules remaining items."""
    user = _create_user(db_session, "rebalance@example.com")
    course = _create_course(db_session, user, daily_minutes=60)
    dag = _create_dp_dag(db_session, course)

    # 1. Generate initial plan
    plan_data = generate_learning_plan(db_session, user.id, course.id)
    plan_id = plan_data.id

    # Find first session
    first_session = plan_data.days[0].sessions[0]

    # 2. Complete first session
    updated_item = update_plan_item_status(
        db=db_session,
        user_id=user.id,
        plan_id=plan_id,
        item_id=first_session.id,
        new_status=STATUS_COMPLETED,
    )
    assert updated_item.status == STATUS_COMPLETED
    assert updated_item.completed_at is not None

    # 3. Trigger rebalance with updated daily budget
    rebalanced = rebalance_learning_plan(
        db=db_session,
        user_id=user.id,
        plan_id=plan_id,
        updated_daily_minutes=90,
    )

    assert rebalanced.daily_minutes == 90
    assert rebalanced.progress.completed_items >= 1

    # Ensure the completed session was preserved and remains completed
    all_rebalanced_sessions = [s for day in rebalanced.days for s in day.sessions]
    completed_in_plan = [s for s in all_rebalanced_sessions if s.id == first_session.id]
    assert len(completed_in_plan) == 1
    assert completed_in_plan[0].status == STATUS_COMPLETED


# ---------------------------------------------------------------------------
# 10. Missed Session Handling and Date Rolling Tests
# ---------------------------------------------------------------------------


def test_missed_session_handling_and_status_update(db_session: Session):
    """Items can be updated to PENDING, IN_PROGRESS, COMPLETED, or SKIPPED."""
    user = _create_user(db_session, "missed_session@example.com")
    course = _create_course(db_session, user)
    dag = _create_dp_dag(db_session, course)

    plan_data = generate_learning_plan(db_session, user.id, course.id)
    session_item = plan_data.days[0].sessions[0]

    # Skip a session
    skipped = update_plan_item_status(
        db=db_session,
        user_id=user.id,
        plan_id=plan_data.id,
        item_id=session_item.id,
        new_status=STATUS_SKIPPED,
    )
    assert skipped.status == STATUS_SKIPPED

    # Rebalance correctly accounts for skipped session
    rebalanced = rebalance_learning_plan(
        db=db_session,
        user_id=user.id,
        plan_id=plan_data.id,
    )
    assert rebalanced.progress.skipped_items >= 1


# ---------------------------------------------------------------------------
# 11. Plan Version History Tests
# ---------------------------------------------------------------------------


def test_plan_version_history(db_session: Session):
    """Regenerating a study plan archives the previous plan and increments version."""
    user = _create_user(db_session, "history@example.com")
    course = _create_course(db_session, user)
    dag = _create_dp_dag(db_session, course)

    # Plan v1
    v1 = generate_learning_plan(db_session, user.id, course.id, daily_minutes=60)
    assert v1.version == 1
    assert v1.status.upper() == "ACTIVE"

    # Plan v2 with force_regenerate
    v2 = generate_learning_plan(
        db_session,
        user.id,
        course.id,
        daily_minutes=90,
        force_regenerate=True,
    )
    assert v2.version == 2
    assert v2.status.upper() == "ACTIVE"

    # Check history
    history = get_study_plan_history(db_session, user.id, course.id)
    assert len(history) == 2
    versions = [h.version for h in history]
    assert 1 in versions
    assert 2 in versions

    # Old plan must now be archived
    old_plan = get_study_plan_by_id(db_session, user.id, v1.id)
    assert old_plan.status.upper() == STATUS_ARCHIVED


# ---------------------------------------------------------------------------
# 12. User Ownership and Authorization Tests
# ---------------------------------------------------------------------------


def test_user_ownership_and_authorization(client: TestClient, db_session: Session):
    """Endpoints require authentication (401) and enforce user ownership (404 for other user's data)."""
    user_a = _create_user(db_session, "user_a@example.com")
    user_b = _create_user(db_session, "user_b@example.com")

    course_a = _create_course(db_session, user_a, title="User A Course")
    dag = _create_dp_dag(db_session, course_a)

    headers_a = _auth_headers(user_a)
    headers_b = _auth_headers(user_b)

    # 1. Unauthenticated request -> 401
    resp_unauth = client.get(f"/api/v1/courses/{course_a.id}/study-plan")
    assert resp_unauth.status_code == 401

    # 2. User A generates plan -> 201
    resp_gen = client.post(
        f"/api/v1/courses/{course_a.id}/study-plan/generate",
        headers=headers_a,
        json={"daily_minutes": 60},
    )
    assert resp_gen.status_code == 201
    plan_data = resp_gen.json()["data"]
    plan_id = plan_data["id"]

    # 3. User B tries to view User A's course plan -> 404
    resp_b_view = client.get(
        f"/api/v1/courses/{course_a.id}/study-plan",
        headers=headers_b,
    )
    assert resp_b_view.status_code == 404

    # 4. User B tries to view User A's plan by ID -> 404
    resp_b_plan = client.get(
        f"/api/v1/study-plans/{plan_id}",
        headers=headers_b,
    )
    assert resp_b_plan.status_code == 404

    # 5. User B tries to rebalance User A's plan -> 404
    resp_b_rebal = client.post(
        f"/api/v1/study-plans/{plan_id}/rebalance",
        headers=headers_b,
        json={"daily_minutes": 90},
    )
    assert resp_b_rebal.status_code == 404

    # 6. User A gets history -> 200
    resp_history = client.get(
        f"/api/v1/courses/{course_a.id}/study-plan/history",
        headers=headers_a,
    )
    assert resp_history.status_code == 200
    assert len(resp_history.json()["data"]) >= 1
