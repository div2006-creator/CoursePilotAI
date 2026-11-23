"""Comprehensive test suite for Part 11: Learning Analytics & Adaptive Progress Intelligence.

Covers:
1. Course overview calculations (total topics, assessed, strong/developing/weak, sessions, average mastery).
2. Missing assessment evidence (honest nulls, unassessed topics not treated as 0% mastery).
3. Topic mastery classification (STRONG >= 80%, DEVELOPING 50-79%, WEAK < 50%, NOT_ASSESSED).
4. Learning improvement measurement (baseline diagnostic vs fresh post-learning assessments).
5. Duplicate question exclusion (duplicate questions excluded from fresh learning improvement proof).
6. True percentage-point calculations (e.g. 35% -> 85% is +50 pp).
7. Learning velocity (topics improved over 7d/30d, weak->dev and dev->strong transitions).
8. Study consistency (completed, skipped, pending, completion rate, daily activity).
9. Honest streak calculation (consecutive calendar days strictly validated, 0 if inactive).
10. Exam readiness score (explainable 40/20/15/15/10 weighted formula & categories).
11. Insufficient assessment coverage penalty (< 40% coverage flags is_reliable = False).
12. Prerequisite bottleneck detection (weak topic blocking dependent topics ranked by impact).
13. Recommendation engine (prioritized, deterministic next best actions).
14. User ownership and data isolation (401 unauthenticated, 404 cross-user access).
15. Full analytics dashboard aggregate endpoint.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys
from typing import Dict
import uuid

# Ensure backend directory is in sys.path
_BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.attempt import Attempt
from app.models.course import Course
from app.models.diagnostic_session import DiagnosticSession, DiagnosticSessionQuestion
from app.models.plan_item import PlanItem
from app.models.question import Question
from app.models.study_plan import StudyPlan
from app.models.topic import Topic
from app.models.topic_mastery import TopicMastery
from app.models.topic_mastery_history import TopicMasteryHistory
from app.models.topic_prerequisite import TopicPrerequisite
from app.models.tutor_session import TutorSession
from app.models.user import User
from app.services.analytics_service import (
    get_course_overview,
    get_diagnostic_comparison,
    get_full_dashboard,
    get_learning_progress,
    get_prerequisite_blockers,
    get_recommended_next_actions,
    get_study_consistency,
    get_topic_mastery_analytics,
    record_mastery_snapshot,
)
from app.services.exam_readiness_service import calculate_exam_readiness


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


def _create_user(session: Session, email: str | None = None) -> User:
    unique_email = email or f"analytics_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        name="Ada Lovelace",
        email=unique_email,
        password_hash="mock_hash_for_testing",
    )
    session.add(user)
    session.flush()
    return user


def _create_course(session: Session, user: User, title: str = "Algorithms Course", exam_date: date | None = None) -> Course:
    course = Course(
        user_id=user.id,
        title=title,
        description="Comprehensive Data Structures & Algorithms",
        daily_minutes=60,
        exam_date=exam_date,
    )
    session.add(course)
    session.flush()
    return course


def _create_topics(session: Session, course: Course) -> Dict[str, Topic]:
    t_recursion = Topic(
        course_id=course.id,
        name="Recursion",
        difficulty="easy",
        unit_name="Unit 1",
    )
    t_dp_state = Topic(
        course_id=course.id,
        name="DP State",
        difficulty="medium",
        unit_name="Unit 2",
    )
    t_tabulation = Topic(
        course_id=course.id,
        name="Tabulation",
        difficulty="medium",
        unit_name="Unit 2",
    )
    t_grid_dp = Topic(
        course_id=course.id,
        name="Grid DP",
        difficulty="hard",
        unit_name="Unit 3",
    )
    session.add_all([t_recursion, t_dp_state, t_tabulation, t_grid_dp])
    session.flush()

    # Prerequisites: Recursion -> DP State -> Tabulation -> Grid DP
    p1 = TopicPrerequisite(topic_id=t_dp_state.id, prerequisite_id=t_recursion.id, confidence=0.95)
    p2 = TopicPrerequisite(topic_id=t_tabulation.id, prerequisite_id=t_dp_state.id, confidence=0.90)
    p3 = TopicPrerequisite(topic_id=t_grid_dp.id, prerequisite_id=t_tabulation.id, confidence=0.90)
    session.add_all([p1, p2, p3])
    session.flush()

    return {
        "recursion": t_recursion,
        "dp_state": t_dp_state,
        "tabulation": t_tabulation,
        "grid_dp": t_grid_dp,
    }


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, extra_claims={"email": user.email})
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Course Overview & Missing Evidence Tests
# ---------------------------------------------------------------------------


def test_course_overview_with_mixed_evidence(db_session: Session):
    """Overview accurately calculates topic classifications and handles unassessed topics honestly."""
    user = _create_user(db_session)
    course = _create_course(db_session, user, exam_date=date.today() + timedelta(days=20))
    topics = _create_topics(db_session, course)

    # 1. Recursion: Strong (mastery = 0.85)
    m_rec = TopicMastery(user_id=user.id, topic_id=topics["recursion"].id, mastery_score=0.85, confidence_score=0.8)
    # 2. DP State: Developing (mastery = 0.65)
    m_dp = TopicMastery(user_id=user.id, topic_id=topics["dp_state"].id, mastery_score=0.65, confidence_score=0.6)
    # 3. Tabulation: Weak (mastery = 0.35)
    m_tab = TopicMastery(user_id=user.id, topic_id=topics["tabulation"].id, mastery_score=0.35, confidence_score=0.4)
    # 4. Grid DP: Unassessed (no TopicMastery, no attempts)
    db_session.add_all([m_rec, m_dp, m_tab])
    db_session.flush()

    overview = get_course_overview(db_session, user.id, course.id)

    assert overview.total_topics == 4
    assert overview.assessed_topics == 3
    assert overview.unassessed_topics == 1
    assert overview.strong_topics == 1
    assert overview.developing_topics == 1
    assert overview.weak_topics == 1

    # Average mastery across ASSESSED topics only: (0.85 + 0.65 + 0.35) / 3 = 0.6166 -> 61.7%
    assert overview.average_mastery_percentage is not None
    assert 61.0 <= overview.average_mastery_percentage <= 62.0
    assert overview.days_remaining == 20


def test_course_overview_all_unassessed_honest_null(db_session: Session):
    """When zero topics have assessment evidence, average mastery is explicitly None."""
    user = _create_user(db_session)
    course = _create_course(db_session, user)
    _create_topics(db_session, course)

    overview = get_course_overview(db_session, user.id, course.id)

    assert overview.total_topics == 4
    assert overview.assessed_topics == 0
    assert overview.unassessed_topics == 4
    assert overview.strong_topics == 0
    assert overview.weak_topics == 0
    assert overview.average_mastery_percentage is None  # Honest null, never treated as 0%


# ---------------------------------------------------------------------------
# 2. Topic Mastery Analytics Tests
# ---------------------------------------------------------------------------


def test_topic_mastery_analytics_breakdown(db_session: Session):
    """Topic mastery analytics returns previous scores, delta, and prerequisite status."""
    user = _create_user(db_session)
    course = _create_course(db_session, user)
    topics = _create_topics(db_session, course)

    # Historical snapshots for Recursion: 0.50 -> 0.85
    rec_id = topics["recursion"].id
    record_mastery_snapshot(db_session, user.id, course.id, rec_id, mastery_score=0.50, recorded_at=datetime.now(timezone.utc) - timedelta(days=5))
    record_mastery_snapshot(db_session, user.id, course.id, rec_id, mastery_score=0.85, recorded_at=datetime.now(timezone.utc))

    m_rec = TopicMastery(user_id=user.id, topic_id=rec_id, mastery_score=0.85, confidence_score=0.9)
    db_session.add(m_rec)
    db_session.flush()

    res = get_topic_mastery_analytics(db_session, user.id, course.id)
    assert res.total_count == 4

    rec_item = next(t for t in res.topics if t.topic_id == rec_id)
    assert rec_item.learning_status == "STRONG"
    assert rec_item.mastery_score == 0.85
    assert rec_item.previous_mastery_score == 0.50
    assert rec_item.mastery_change == 0.35  # 0.85 - 0.50

    # Grid DP requires Tabulation which is unassessed -> prerequisite should NOT be satisfied
    grid_item = next(t for t in res.topics if t.topic_id == topics["grid_dp"].id)
    assert grid_item.learning_status == "NOT_ASSESSED"
    assert not grid_item.is_prerequisite_satisfied
    assert "Tabulation" in grid_item.unmet_prerequisites


# ---------------------------------------------------------------------------
# 3. Learning Improvement & Diagnostic Comparison Tests
# ---------------------------------------------------------------------------


def test_learning_improvement_measures_actual_fresh_progress(db_session: Session):
    """Compares baseline diagnostic to fresh post-learning questions with percentage-point delta."""
    user = _create_user(db_session)
    course = _create_course(db_session, user)
    topics = _create_topics(db_session, course)
    topic_dp = topics["dp_state"]

    # 1. Baseline Diagnostic Session (3 questions on DP State: 1 correct, 2 incorrect = 33.3%)
    diag_sess = DiagnosticSession(
        user_id=user.id,
        course_id=course.id,
        status="completed",
        score=33.3,
        total_questions=3,
        correct_answers=1,
        started_at=datetime.now(timezone.utc) - timedelta(days=3),
        completed_at=datetime.now(timezone.utc) - timedelta(days=3),
    )
    db_session.add(diag_sess)
    db_session.flush()

    q_base1 = Question(topic_id=topic_dp.id, question="Base Q1", options=["A", "B"], correct_answer="A", difficulty="medium")
    q_base2 = Question(topic_id=topic_dp.id, question="Base Q2", options=["A", "B"], correct_answer="A", difficulty="medium")
    q_base3 = Question(topic_id=topic_dp.id, question="Base Q3", options=["A", "B"], correct_answer="A", difficulty="medium")
    db_session.add_all([q_base1, q_base2, q_base3])
    db_session.flush()

    att_b1 = Attempt(user_id=user.id, course_id=course.id, topic_id=topic_dp.id, question_id=q_base1.id, diagnostic_session_id=diag_sess.id, selected_answer="A", is_correct=True, created_at=diag_sess.completed_at)
    att_b2 = Attempt(user_id=user.id, course_id=course.id, topic_id=topic_dp.id, question_id=q_base2.id, diagnostic_session_id=diag_sess.id, selected_answer="B", is_correct=False, created_at=diag_sess.completed_at)
    att_b3 = Attempt(user_id=user.id, course_id=course.id, topic_id=topic_dp.id, question_id=q_base3.id, diagnostic_session_id=diag_sess.id, selected_answer="B", is_correct=False, created_at=diag_sess.completed_at)
    db_session.add_all([att_b1, att_b2, att_b3])
    db_session.flush()

    # 2. Fresh Post-Learning Practice Session (3 fresh novel questions: all 3 correct = 100.0%)
    q_fresh1 = Question(topic_id=topic_dp.id, question="Fresh Q1", options=["A", "B"], correct_answer="A", difficulty="medium")
    q_fresh2 = Question(topic_id=topic_dp.id, question="Fresh Q2", options=["A", "B"], correct_answer="A", difficulty="medium")
    q_fresh3 = Question(topic_id=topic_dp.id, question="Fresh Q3", options=["A", "B"], correct_answer="A", difficulty="medium")
    db_session.add_all([q_fresh1, q_fresh2, q_fresh3])
    db_session.flush()

    tutor_sess = TutorSession(user_id=user.id, course_id=course.id, topic_id=topic_dp.id, status="ACTIVE", current_stage="PRACTICE")
    db_session.add(tutor_sess)
    db_session.flush()

    post_time = datetime.now(timezone.utc) - timedelta(days=1)
    att_f1 = Attempt(user_id=user.id, course_id=course.id, topic_id=topic_dp.id, question_id=q_fresh1.id, tutor_session_id=tutor_sess.id, selected_answer="A", is_correct=True, created_at=post_time)
    att_f2 = Attempt(user_id=user.id, course_id=course.id, topic_id=topic_dp.id, question_id=q_fresh2.id, tutor_session_id=tutor_sess.id, selected_answer="A", is_correct=True, created_at=post_time)
    att_f3 = Attempt(user_id=user.id, course_id=course.id, topic_id=topic_dp.id, question_id=q_fresh3.id, tutor_session_id=tutor_sess.id, selected_answer="A", is_correct=True, created_at=post_time)
    db_session.add_all([att_f1, att_f2, att_f3])
    db_session.flush()

    improvement = get_diagnostic_comparison(db_session, user.id, course.id)

    assert improvement.has_sufficient_data
    assert improvement.total_comparisons == 1
    assert improvement.improved_topics_count == 1

    comp = improvement.comparisons[0]
    assert comp.topic_id == topic_dp.id
    assert comp.baseline_score == 33.3
    assert comp.latest_score == 100.0
    # Absolute percentage-point change: 100.0 - 33.3 = +66.7 pp
    assert comp.percentage_point_improvement == 66.7
    assert comp.is_fresh
    assert comp.evidence_quality == "HIGH"


def test_learning_improvement_excludes_duplicate_questions(db_session: Session):
    """Answering the same baseline question again is excluded from verified fresh learning improvement."""
    user = _create_user(db_session)
    course = _create_course(db_session, user)
    topics = _create_topics(db_session, course)
    topic_dp = topics["dp_state"]

    # Baseline diagnostic with Q1 (incorrect)
    diag_time = datetime.now(timezone.utc) - timedelta(days=3)
    diag_sess = DiagnosticSession(user_id=user.id, course_id=course.id, status="completed", score=0.0, started_at=diag_time, completed_at=diag_time)
    q1 = Question(topic_id=topic_dp.id, question="Repeated Q1", options=["A", "B"], correct_answer="A")
    db_session.add_all([diag_sess, q1])
    db_session.flush()

    att1 = Attempt(user_id=user.id, course_id=course.id, topic_id=topic_dp.id, question_id=q1.id, diagnostic_session_id=diag_sess.id, selected_answer="B", is_correct=False, created_at=diag_time)
    db_session.add(att1)
    db_session.flush()

    # Later: student re-attempts the exact same Q1 and gets it right
    post_time = datetime.now(timezone.utc) - timedelta(days=1)
    att_dup = Attempt(user_id=user.id, course_id=course.id, topic_id=topic_dp.id, question_id=q1.id, selected_answer="A", is_correct=True, created_at=post_time)
    db_session.add(att_dup)
    db_session.flush()

    # The engine should exclude repeated Q1 as fresh proof of learning
    improvement = get_diagnostic_comparison(db_session, user.id, course.id)
    assert improvement.improved_topics_count == 0
    comp = improvement.comparisons[0]
    assert comp.latest_score is None  # No fresh questions answered
    assert comp.evidence_quality == "INSUFFICIENT"


# ---------------------------------------------------------------------------
# 4. Learning Velocity Tests
# ---------------------------------------------------------------------------


def test_learning_velocity_and_transitions(db_session: Session):
    """Calculates topics graduated across thresholds and recent velocity."""
    user = _create_user(db_session)
    course = _create_course(db_session, user)
    topics = _create_topics(db_session, course)

    now = datetime.now(timezone.utc)
    # Recursion: WEAK (0.30) 10 days ago -> DEVELOPING (0.60) 6 days ago -> STRONG (0.85) today
    rec_id = topics["recursion"].id
    record_mastery_snapshot(db_session, user.id, course.id, rec_id, 0.30, recorded_at=now - timedelta(days=10))
    record_mastery_snapshot(db_session, user.id, course.id, rec_id, 0.60, recorded_at=now - timedelta(days=6))
    record_mastery_snapshot(db_session, user.id, course.id, rec_id, 0.85, recorded_at=now)

    progress = get_learning_progress(db_session, user.id, course.id)
    velocity = progress.velocity

    assert velocity.topics_improved_7d >= 1
    assert velocity.topics_improved_30d >= 1
    assert velocity.transitions_weak_to_developing >= 1
    assert velocity.transitions_developing_to_strong >= 1
    assert velocity.velocity_status in ("ACCELERATING", "STEADY")


# ---------------------------------------------------------------------------
# 5. Study Consistency & Streak Tests
# ---------------------------------------------------------------------------


def test_study_consistency_honest_consecutive_streak(db_session: Session):
    """Streak is strictly based on consecutive calendar days with completed study activity."""
    user = _create_user(db_session)
    course = _create_course(db_session, user)
    topics = _create_topics(db_session, course)

    plan = StudyPlan(user_id=user.id, course_id=course.id, version=1, status="active")
    db_session.add(plan)
    db_session.flush()

    today = date.today()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)
    four_days_ago = today - timedelta(days=4)

    # Completed items on today, yesterday, and two days ago -> 3-day streak!
    item1 = PlanItem(plan_id=plan.id, topic_id=topics["recursion"].id, scheduled_date=today, duration_minutes=45, status="COMPLETED", completed_at=datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc))
    item2 = PlanItem(plan_id=plan.id, topic_id=topics["dp_state"].id, scheduled_date=yesterday, duration_minutes=60, status="COMPLETED", completed_at=datetime.combine(yesterday, datetime.min.time(), tzinfo=timezone.utc))
    item3 = PlanItem(plan_id=plan.id, topic_id=topics["tabulation"].id, scheduled_date=two_days_ago, duration_minutes=30, status="COMPLETED", completed_at=datetime.combine(two_days_ago, datetime.min.time(), tzinfo=timezone.utc))
    # Skipped session 4 days ago
    item4 = PlanItem(plan_id=plan.id, topic_id=topics["grid_dp"].id, scheduled_date=four_days_ago, duration_minutes=60, status="SKIPPED")
    db_session.add_all([item1, item2, item3, item4])
    db_session.flush()

    consistency = get_study_consistency(db_session, user.id, course.id)

    assert consistency.completed_sessions == 3
    assert consistency.skipped_sessions == 1
    assert consistency.completion_rate == 75.0  # 3 / 4 = 75%
    assert consistency.active_study_days >= 3
    assert consistency.current_streak_days == 3


def test_study_consistency_broken_streak_returns_zero(db_session: Session):
    """If no activity occurred today or yesterday, streak is 0 (never fabricated)."""
    user = _create_user(db_session)
    course = _create_course(db_session, user)
    topics = _create_topics(db_session, course)

    plan = StudyPlan(user_id=user.id, course_id=course.id, version=1, status="active")
    db_session.add(plan)
    db_session.flush()

    three_days_ago = date.today() - timedelta(days=3)
    item = PlanItem(plan_id=plan.id, topic_id=topics["recursion"].id, scheduled_date=three_days_ago, duration_minutes=45, status="COMPLETED", completed_at=datetime.combine(three_days_ago, datetime.min.time(), tzinfo=timezone.utc))
    db_session.add(item)
    db_session.flush()

    consistency = get_study_consistency(db_session, user.id, course.id)
    assert consistency.current_streak_days == 0  # Inactive yesterday and today -> streak 0


# ---------------------------------------------------------------------------
# 6. Exam Readiness Engine Tests
# ---------------------------------------------------------------------------


def test_exam_readiness_insufficient_coverage_flagged(db_session: Session):
    """When assessment coverage is below 40%, is_reliable is False with explicit warning."""
    user = _create_user(db_session)
    course = _create_course(db_session, user)
    topics = _create_topics(db_session, course)  # 4 topics total

    # Only 1 of 4 topics assessed = 25% coverage (< 40% threshold)
    rec_id = topics["recursion"].id
    m_rec = TopicMastery(user_id=user.id, topic_id=rec_id, mastery_score=0.90)
    db_session.add(m_rec)
    db_session.flush()

    readiness = calculate_exam_readiness(db_session, user.id, course.id)

    assert readiness.assessment_coverage_percentage == 25.0
    assert not readiness.is_reliable
    assert readiness.coverage_warning is not None
    assert "is provisional" in readiness.coverage_warning


def test_exam_readiness_comprehensive_score_and_components(db_session: Session):
    """High mastery across all topics produces high readiness score and Exam Ready category."""
    user = _create_user(db_session)
    course = _create_course(db_session, user, exam_date=date.today() + timedelta(days=15))
    topics = _create_topics(db_session, course)

    # Set all 4 topics to high mastery
    for t in topics.values():
        m = TopicMastery(user_id=user.id, topic_id=t.id, mastery_score=0.92, confidence_score=0.9)
        db_session.add(m)
        q = Question(topic_id=t.id, question=f"Q {t.name}", options=["A", "B"], correct_answer="A")
        db_session.add(q)
        db_session.flush()
        att = Attempt(user_id=user.id, course_id=course.id, topic_id=t.id, question_id=q.id, selected_answer="A", is_correct=True)
        db_session.add(att)

    db_session.flush()

    readiness = calculate_exam_readiness(db_session, user.id, course.id)

    assert readiness.assessment_coverage_percentage == 100.0
    assert readiness.is_reliable
    assert readiness.readiness_score >= 85.0
    assert readiness.category == "Exam Ready"
    assert readiness.days_remaining == 15
    assert readiness.weak_topics_count == 0


# ---------------------------------------------------------------------------
# 7. Prerequisite Bottlenecks & Recommendations Tests
# ---------------------------------------------------------------------------


def test_prerequisite_bottleneck_detection(db_session: Session):
    """Detects weak foundational topic that blocks multiple downstream concepts."""
    user = _create_user(db_session)
    course = _create_course(db_session, user)
    topics = _create_topics(db_session, course)

    # Recursion is weak (< 0.50). Recursion is prerequisite to DP State, which is prereq to Tabulation and Grid DP
    m_rec = TopicMastery(user_id=user.id, topic_id=topics["recursion"].id, mastery_score=0.25)
    db_session.add(m_rec)
    db_session.flush()

    blockers = get_prerequisite_blockers(db_session, user.id, course.id)
    assert len(blockers) >= 1

    rec_blocker = next(b for b in blockers if b.topic_id == topics["recursion"].id)
    assert rec_blocker.bottleneck_impact_score > 0
    assert "DP State" in rec_blocker.blocked_topics_names
    assert "Recursion" in rec_blocker.explanation


def test_recommendation_engine_generates_actionable_steps(db_session: Session):
    """Recommendations prioritize bottleneck resolution, active study plan, and weak areas."""
    user = _create_user(db_session)
    course = _create_course(db_session, user, exam_date=date.today() + timedelta(days=7))
    topics = _create_topics(db_session, course)

    # Weak recursion
    m_rec = TopicMastery(user_id=user.id, topic_id=topics["recursion"].id, mastery_score=0.30)
    # Developing DP state
    m_dp = TopicMastery(user_id=user.id, topic_id=topics["dp_state"].id, mastery_score=0.65)
    db_session.add_all([m_rec, m_dp])
    db_session.flush()

    recs = get_recommended_next_actions(db_session, user.id, course.id)
    assert len(recs) >= 2

    # High priority bottleneck recommendation should exist
    action_types = {r.action_type for r in recs}
    assert "TUTOR" in action_types or "STUDY_PLAN" in action_types
    # Exam countdown recommendation should be present because exam <= 14 days
    assert any("Exam" in r.title for r in recs)


# ---------------------------------------------------------------------------
# 8. API Endpoints & Authorization Tests
# ---------------------------------------------------------------------------


def test_analytics_endpoints_ownership_and_authorization(client: TestClient, db_session: Session):
    """Enforces 401 unauthenticated and 404 cross-user data isolation."""
    user_a = _create_user(db_session)
    user_b = _create_user(db_session)
    course_a = _create_course(db_session, user_a)
    _create_topics(db_session, course_a)

    headers_a = _auth_headers(user_a)
    headers_b = _auth_headers(user_b)

    # 1. Unauthenticated -> 401
    resp_unauth = client.get(f"/api/v1/courses/{course_a.id}/analytics/overview")
    assert resp_unauth.status_code == 401

    # 2. User A accesses own course -> 200
    resp_a = client.get(f"/api/v1/courses/{course_a.id}/analytics/overview", headers=headers_a)
    assert resp_a.status_code == 200
    assert resp_a.json()["data"]["total_topics"] == 4

    # 3. User B accesses User A's course -> 404 (data isolation)
    resp_b = client.get(f"/api/v1/courses/{course_a.id}/analytics/overview", headers=headers_b)
    assert resp_b.status_code == 404


def test_full_analytics_dashboard_endpoint(client: TestClient, db_session: Session):
    """Full dashboard endpoint aggregates overview, mastery, consistency, readiness, and bottlenecks."""
    user = _create_user(db_session)
    course = _create_course(db_session, user)
    _create_topics(db_session, course)
    headers = _auth_headers(user)

    resp = client.get(f"/api/v1/courses/{course.id}/analytics", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert "overview" in data
    assert "mastery_analytics" in data
    assert "improvement" in data
    assert "progress" in data
    assert "consistency" in data
    assert "exam_readiness" in data
    assert "bottlenecks" in data
    assert "recommendations" in data
