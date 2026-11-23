"""Learning Analytics and Adaptive Progress Intelligence Service.

Computes 100% deterministic, explainable learning analytics based strictly on real
recorded attempts, diagnostic sessions, study plan items, and prerequisite graphs.
Never fabricates statistics, streaks, hours, or improvement scores.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import utc_now
from app.models.attempt import Attempt
from app.models.course import Course
from app.models.diagnostic_session import DiagnosticSession
from app.models.plan_item import PlanItem
from app.models.study_plan import StudyPlan
from app.models.topic import Topic
from app.models.topic_mastery import TopicMastery
from app.models.topic_mastery_history import TopicMasteryHistory
from app.models.topic_prerequisite import TopicPrerequisite
from app.schemas.analytics import (
    CourseOverviewResponseData,
    DailyActivityPoint,
    DiagnosticComparisonItem,
    FullAnalyticsDashboardResponseData,
    LearningImprovementResponseData,
    LearningProgressPoint,
    LearningProgressResponseData,
    LearningVelocityData,
    PrerequisiteBlockerItem,
    RecommendationItem,
    StudyConsistencyResponseData,
    TopicMasteryAnalyticsResponseData,
    TopicMasteryItem,
)
from app.services.exam_readiness_service import calculate_exam_readiness

# Thresholds established in Part 8 (Knowledge Gap Analysis)
STRONG_THRESHOLD = 0.80  # 80.0%
DEVELOPING_THRESHOLD = 0.50  # 50.0%


class CourseAccessDeniedError(Exception):
    """Raised when an unauthenticated or unauthorized user requests another's course analytics."""


def _as_utc(dt: datetime) -> datetime:
    """Ensure datetime is offset-aware in UTC (fixes SQLite naive datetime issues)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _verify_course_ownership(db: Session, user_id: uuid.UUID, course_id: uuid.UUID) -> Course:
    course = db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user_id)
    ).scalar_one_or_none()
    if not course:
        raise CourseAccessDeniedError(f"Course {course_id} not found or access denied.")
    return course


# ---------------------------------------------------------------------------
# 0. Historical Snapshot Helper
# ---------------------------------------------------------------------------


def record_mastery_snapshot(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
    topic_id: uuid.UUID,
    mastery_score: float,
    confidence_score: float = 0.0,
    evidence_count: int = 0,
    assessment_type: str = "PRACTICE",
    recorded_at: Optional[datetime] = None,
) -> TopicMasteryHistory:
    """Record an immutable mastery snapshot for longitudinal velocity and comparison tracking."""
    snapshot = TopicMasteryHistory(
        user_id=user_id,
        course_id=course_id,
        topic_id=topic_id,
        mastery_score=round(min(1.0, max(0.0, mastery_score)), 3),
        confidence_score=round(min(1.0, max(0.0, confidence_score)), 3),
        evidence_count=max(0, evidence_count),
        assessment_type=assessment_type,
        recorded_at=recorded_at or utc_now(),
    )
    db.add(snapshot)
    db.flush()
    return snapshot


# ---------------------------------------------------------------------------
# 1. Course Overview
# ---------------------------------------------------------------------------


def get_course_overview(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
) -> CourseOverviewResponseData:
    """Calculate aggregate course learning metrics from real evidence."""
    course = _verify_course_ownership(db, user_id, course_id)

    topics = db.execute(
        select(Topic).where(Topic.course_id == course_id)
    ).scalars().all()
    total_topics = len(topics)
    topic_ids = [t.id for t in topics]

    if total_topics == 0:
        return CourseOverviewResponseData(
            total_topics=0,
            assessed_topics=0,
            strong_topics=0,
            developing_topics=0,
            weak_topics=0,
            unassessed_topics=0,
            completed_study_sessions=0,
            pending_study_sessions=0,
            total_practice_attempts=0,
            average_mastery_percentage=None,
            active_plan_id=None,
            active_plan_version=None,
            exam_date=course.exam_date.isoformat() if course.exam_date else None,
            days_remaining=(course.exam_date - date.today()).days if course.exam_date else None,
        )

    # Topic Masteries
    masteries = db.execute(
        select(TopicMastery).where(
            TopicMastery.user_id == user_id,
            TopicMastery.topic_id.in_(topic_ids),
        )
    ).scalars().all()
    mastery_map = {m.topic_id: m.mastery_score for m in masteries}

    # Attempts
    attempts = db.execute(
        select(Attempt).where(
            Attempt.user_id == user_id,
            Attempt.course_id == course_id,
        )
    ).scalars().all()
    attempts_by_topic: Dict[uuid.UUID, List[Attempt]] = defaultdict(list)
    for a in attempts:
        attempts_by_topic[a.topic_id].append(a)

    practice_attempts_count = sum(1 for a in attempts if a.tutor_session_id is not None)

    # Classification
    strong_cnt = 0
    dev_cnt = 0
    weak_cnt = 0
    unassessed_cnt = 0
    assessed_mastery_sum = 0.0
    assessed_topics_cnt = 0

    for t in topics:
        t_attempts = attempts_by_topic.get(t.id, [])
        has_evidence = len(t_attempts) > 0 or t.id in mastery_map

        if not has_evidence:
            unassessed_cnt += 1
        else:
            assessed_topics_cnt += 1
            # Use TopicMastery score if available, or compute from attempts
            if t.id in mastery_map:
                score = mastery_map[t.id]
            elif t_attempts:
                score = sum(1 for a in t_attempts if a.is_correct) / len(t_attempts)
            else:
                score = 0.0

            assessed_mastery_sum += score

            if score >= STRONG_THRESHOLD:
                strong_cnt += 1
            elif score >= DEVELOPING_THRESHOLD:
                dev_cnt += 1
            else:
                weak_cnt += 1

    avg_mastery_pct = (
        round((assessed_mastery_sum / assessed_topics_cnt) * 100.0, 1)
        if assessed_topics_cnt > 0
        else None
    )

    # Active Study Plan
    active_plan = db.execute(
        select(StudyPlan)
        .where(
            StudyPlan.user_id == user_id,
            StudyPlan.course_id == course_id,
            StudyPlan.status == "active",
        )
        .order_by(StudyPlan.version.desc())
    ).scalar_one_or_none()

    completed_sessions = 0
    pending_sessions = 0
    if active_plan:
        plan_items = db.execute(
            select(PlanItem).where(PlanItem.plan_id == active_plan.id)
        ).scalars().all()
        for item in plan_items:
            st = item.status.upper()
            if st == "COMPLETED":
                completed_sessions += 1
            elif st in ("PENDING", "IN_PROGRESS"):
                pending_sessions += 1

    days_rem = (course.exam_date - date.today()).days if course.exam_date else None

    return CourseOverviewResponseData(
        total_topics=total_topics,
        assessed_topics=assessed_topics_cnt,
        strong_topics=strong_cnt,
        developing_topics=dev_cnt,
        weak_topics=weak_cnt,
        unassessed_topics=unassessed_cnt,
        completed_study_sessions=completed_sessions,
        pending_study_sessions=pending_sessions,
        total_practice_attempts=practice_attempts_count,
        average_mastery_percentage=avg_mastery_pct,
        active_plan_id=active_plan.id if active_plan else None,
        active_plan_version=active_plan.version if active_plan else None,
        exam_date=course.exam_date.isoformat() if course.exam_date else None,
        days_remaining=days_rem,
    )


# ---------------------------------------------------------------------------
# 2. Topic Mastery Analytics
# ---------------------------------------------------------------------------


def get_topic_mastery_analytics(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
) -> TopicMasteryAnalyticsResponseData:
    """Provide detailed evidence breakdown and learning status for all topics."""
    _verify_course_ownership(db, user_id, course_id)

    topics = db.execute(
        select(Topic).where(Topic.course_id == course_id).order_by(Topic.name.asc())
    ).scalars().all()
    topic_ids = [t.id for t in topics]

    if not topics:
        return TopicMasteryAnalyticsResponseData(
            topics=[],
            total_count=0,
            strong_count=0,
            developing_count=0,
            weak_count=0,
            unassessed_count=0,
        )

    # Masteries
    masteries = db.execute(
        select(TopicMastery).where(
            TopicMastery.user_id == user_id,
            TopicMastery.topic_id.in_(topic_ids),
        )
    ).scalars().all()
    mastery_map: Dict[uuid.UUID, TopicMastery] = {m.topic_id: m for m in masteries}

    # Historical Snapshots (find second-to-latest snapshot for previous_mastery_score)
    history_rows = db.execute(
        select(TopicMasteryHistory)
        .where(
            TopicMasteryHistory.user_id == user_id,
            TopicMasteryHistory.course_id == course_id,
        )
        .order_by(TopicMasteryHistory.topic_id, TopicMasteryHistory.recorded_at.desc())
    ).scalars().all()
    history_by_topic: Dict[uuid.UUID, List[TopicMasteryHistory]] = defaultdict(list)
    for h in history_rows:
        history_by_topic[h.topic_id].append(h)

    # Attempts
    attempts = db.execute(
        select(Attempt)
        .where(Attempt.user_id == user_id, Attempt.course_id == course_id)
        .order_by(Attempt.created_at.asc())
    ).scalars().all()
    attempts_by_topic: Dict[uuid.UUID, List[Attempt]] = defaultdict(list)
    for a in attempts:
        attempts_by_topic[a.topic_id].append(a)

    # Prerequisites graph
    prereqs = db.execute(
        select(TopicPrerequisite).where(
            TopicPrerequisite.topic_id.in_(topic_ids),
            TopicPrerequisite.prerequisite_id.in_(topic_ids),
        )
    ).scalars().all()
    prereqs_map: Dict[uuid.UUID, List[uuid.UUID]] = defaultdict(list)
    topic_name_map: Dict[uuid.UUID, str] = {t.id: t.name for t in topics}
    for p in prereqs:
        prereqs_map[p.topic_id].append(p.prerequisite_id)

    items: List[TopicMasteryItem] = []
    strong_c = 0
    dev_c = 0
    weak_c = 0
    unassessed_c = 0

    for t in topics:
        t_attempts = attempts_by_topic.get(t.id, [])
        m_rec = mastery_map.get(t.id)
        has_evidence = len(t_attempts) > 0 or m_rec is not None

        # Check prerequisites satisfaction
        unmet_prereqs: List[str] = []
        is_prereq_satisfied = True
        for p_id in prereqs_map.get(t.id, []):
            p_score = mastery_map[p_id].mastery_score if p_id in mastery_map else None
            # If prerequisite is not assessed or weak (< 0.50), mark unmet
            if p_score is None or p_score < DEVELOPING_THRESHOLD:
                is_prereq_satisfied = False
                unmet_prereqs.append(topic_name_map.get(p_id, "Unknown Topic"))

        if not has_evidence:
            unassessed_c += 1
            rec_action = (
                f"Master prerequisite {unmet_prereqs[0]} first"
                if unmet_prereqs
                else "Take diagnostic assessment"
            )
            items.append(
                TopicMasteryItem(
                    topic_id=t.id,
                    topic_name=t.name,
                    unit_name=t.unit_name,
                    difficulty=t.difficulty,
                    mastery_score=None,
                    mastery_percentage=None,
                    previous_mastery_score=None,
                    mastery_change=None,
                    diagnostic_accuracy=None,
                    latest_practice_accuracy=None,
                    evidence_count=0,
                    last_assessed_at=None,
                    learning_status="NOT_ASSESSED",
                    is_prerequisite_satisfied=is_prereq_satisfied,
                    unmet_prerequisites=unmet_prereqs,
                    recommended_action=rec_action,
                )
            )
            continue

        # Current Score
        current_score = m_rec.mastery_score if m_rec else (
            sum(1 for a in t_attempts if a.is_correct) / len(t_attempts)
        )
        current_pct = round(current_score * 100.0, 1)

        # Previous Score
        t_hist = history_by_topic.get(t.id, [])
        prev_score: Optional[float] = None
        if len(t_hist) > 1:
            prev_score = t_hist[1].mastery_score
        elif len(t_hist) == 1 and m_rec and abs(m_rec.mastery_score - t_hist[0].mastery_score) > 0.001:
            prev_score = t_hist[0].mastery_score

        m_change = round(current_score - prev_score, 3) if prev_score is not None else None

        # Diagnostic Accuracy
        diag_attempts = [a for a in t_attempts if a.diagnostic_session_id is not None]
        diag_acc = (
            round((sum(1 for a in diag_attempts if a.is_correct) / len(diag_attempts)) * 100.0, 1)
            if diag_attempts
            else None
        )

        # Latest Practice Accuracy
        practice_attempts = [a for a in t_attempts if a.tutor_session_id is not None]
        latest_pract_acc = (
            (100.0 if practice_attempts[-1].is_correct else 0.0)
            if practice_attempts
            else None
        )

        # Last assessed timestamp
        last_dt = (
            m_rec.last_assessed_at
            if m_rec and m_rec.last_assessed_at
            else (t_attempts[-1].created_at if t_attempts else None)
        )

        # Status
        if current_score >= STRONG_THRESHOLD:
            status = "STRONG"
            strong_c += 1
            rec_action = "Review periodic refreshers before exam"
        elif current_score >= DEVELOPING_THRESHOLD:
            status = "DEVELOPING"
            dev_c += 1
            rec_action = "Solve medium-level practice problems in AI Tutor"
        else:
            status = "WEAK"
            weak_c += 1
            if unmet_prereqs:
                rec_action = f"Foundational gap: revise prerequisite {unmet_prereqs[0]}"
            else:
                rec_action = "Launch 1-on-1 AI Tutor concept explanation"

        items.append(
            TopicMasteryItem(
                topic_id=t.id,
                topic_name=t.name,
                unit_name=t.unit_name,
                difficulty=t.difficulty,
                mastery_score=round(current_score, 3),
                mastery_percentage=current_pct,
                previous_mastery_score=prev_score,
                mastery_change=m_change,
                diagnostic_accuracy=diag_acc,
                latest_practice_accuracy=latest_pract_acc,
                evidence_count=len(t_attempts),
                last_assessed_at=last_dt,
                learning_status=status,
                is_prerequisite_satisfied=is_prereq_satisfied,
                unmet_prerequisites=unmet_prereqs,
                recommended_action=rec_action,
            )
        )

    return TopicMasteryAnalyticsResponseData(
        topics=items,
        total_count=len(items),
        strong_count=strong_c,
        developing_count=dev_c,
        weak_count=weak_c,
        unassessed_count=unassessed_c,
    )


# ---------------------------------------------------------------------------
# 3. Learning Improvement & Diagnostic Comparison
# ---------------------------------------------------------------------------


def get_diagnostic_comparison(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
) -> LearningImprovementResponseData:
    """Measure actual learning improvement by comparing baseline diagnostic against fresh assessments.

    Guarantees:
    - Identical repeated questions are excluded from fresh improvement proof.
    - Uses true percentage-point (pp) delta, not misleading percentage growth.
    - Honors 'Not enough assessment data' when post-learning evidence is missing.
    """
    _verify_course_ownership(db, user_id, course_id)

    topics = db.execute(
        select(Topic).where(Topic.course_id == course_id).order_by(Topic.name.asc())
    ).scalars().all()
    topic_map = {t.id: t for t in topics}

    if not topics:
        return LearningImprovementResponseData(
            has_sufficient_data=False,
            total_comparisons=0,
            improved_topics_count=0,
            stagnant_topics_count=0,
            regressed_topics_count=0,
            average_percentage_point_change=None,
            comparisons=[],
            explanation="No topics in this course to compare.",
        )

    # Fetch all diagnostic sessions for this course, ordered chronologically
    diag_sessions = db.execute(
        select(DiagnosticSession)
        .where(
            DiagnosticSession.user_id == user_id,
            DiagnosticSession.course_id == course_id,
            DiagnosticSession.status == "completed",
        )
        .order_by(DiagnosticSession.completed_at.asc())
    ).scalars().all()

    # Fetch all attempts for this user & course, ordered chronologically
    attempts = db.execute(
        select(Attempt)
        .where(Attempt.user_id == user_id, Attempt.course_id == course_id)
        .order_by(Attempt.created_at.asc())
    ).scalars().all()

    attempts_by_topic: Dict[uuid.UUID, List[Attempt]] = defaultdict(list)
    for a in attempts:
        attempts_by_topic[a.topic_id].append(a)

    comparisons: List[DiagnosticComparisonItem] = []
    improved_cnt = 0
    stagnant_cnt = 0
    regressed_cnt = 0
    total_pp_sum = 0.0
    valid_pp_comparisons = 0

    for topic_id, t_attempts in attempts_by_topic.items():
        if topic_id not in topic_map:
            continue

        topic = topic_map[topic_id]

        # 1. Identify baseline diagnostic attempts
        # Baseline = attempts belonging to earliest completed diagnostic session covering this topic
        diag_attempts = [a for a in t_attempts if a.diagnostic_session_id is not None]
        if not diag_attempts:
            continue  # No baseline diagnostic for this topic

        first_diag_sess_id = diag_attempts[0].diagnostic_session_id
        baseline_attempts = [a for a in diag_attempts if a.diagnostic_session_id == first_diag_sess_id]

        if not baseline_attempts:
            continue

        baseline_q_count = len(baseline_attempts)
        baseline_correct = sum(1 for a in baseline_attempts if a.is_correct)
        baseline_acc = round((baseline_correct / baseline_q_count) * 100.0, 1)
        baseline_date = baseline_attempts[-1].created_at
        baseline_question_ids = {a.question_id for a in baseline_attempts}

        # 2. Identify post-learning fresh attempts (recorded strictly after baseline_date)
        post_attempts = [a for a in t_attempts if a.created_at > baseline_date]

        # EXCLUDE DUPLICATE QUESTIONS: proof of learning requires answering novel/fresh problems
        fresh_attempts = [a for a in post_attempts if a.question_id not in baseline_question_ids]

        if not fresh_attempts:
            # Insufficient post-learning assessment data
            comparisons.append(
                DiagnosticComparisonItem(
                    topic_id=topic.id,
                    topic_name=topic.name,
                    unit_name=topic.unit_name,
                    baseline_score=baseline_acc,
                    latest_score=None,
                    percentage_point_improvement=None,
                    baseline_questions_count=baseline_q_count,
                    latest_questions_count=0,
                    baseline_date=baseline_date,
                    latest_date=None,
                    evidence_quality="INSUFFICIENT",
                    is_fresh=True,
                    status_label="Not enough assessment data. Complete fresh practice problems to verify improvement.",
                )
            )
            continue

        fresh_q_count = len(fresh_attempts)
        fresh_correct = sum(1 for a in fresh_attempts if a.is_correct)
        latest_acc = round((fresh_correct / fresh_q_count) * 100.0, 1)
        latest_date = fresh_attempts[-1].created_at
        pp_change = round(latest_acc - baseline_acc, 1)

        # Evidence quality: depends on fresh question sample size
        if fresh_q_count >= 3:
            quality = "HIGH"
        elif fresh_q_count == 2:
            quality = "MEDIUM"
        else:
            quality = "LOW"

        # Cautious pedagogical label (never claims unproven causality)
        if pp_change > 0:
            status_lbl = f"Observed performance improvement: +{pp_change} pp on {fresh_q_count} fresh question(s)"
            improved_cnt += 1
        elif pp_change == 0:
            status_lbl = f"Observed stable performance (0.0 pp change across {fresh_q_count} fresh questions)"
            stagnant_cnt += 1
        else:
            status_lbl = f"Observed performance decrease ({pp_change} pp) on fresh problems"
            regressed_cnt += 1

        total_pp_sum += pp_change
        valid_pp_comparisons += 1

        comparisons.append(
            DiagnosticComparisonItem(
                topic_id=topic.id,
                topic_name=topic.name,
                unit_name=topic.unit_name,
                baseline_score=baseline_acc,
                latest_score=latest_acc,
                percentage_point_improvement=pp_change,
                baseline_questions_count=baseline_q_count,
                latest_questions_count=fresh_q_count,
                baseline_date=baseline_date,
                latest_date=latest_date,
                evidence_quality=quality,
                is_fresh=True,
                status_label=status_lbl,
            )
        )

    has_data = valid_pp_comparisons > 0
    avg_pp = (
        round(total_pp_sum / valid_pp_comparisons, 1)
        if valid_pp_comparisons > 0
        else None
    )

    if has_data:
        expl = (
            f"Compared initial diagnostic with fresh post-learning questions across {valid_pp_comparisons} topic(s). "
            f"Average observed performance delta is {f'+{avg_pp}' if avg_pp and avg_pp > 0 else avg_pp} percentage points."
        )
    else:
        expl = (
            "No fresh post-diagnostic assessments recorded yet. Complete AI Tutor practice problems "
            "or fresh diagnostics to measure verified learning improvement."
        )

    return LearningImprovementResponseData(
        has_sufficient_data=has_data,
        total_comparisons=len(comparisons),
        improved_topics_count=improved_cnt,
        stagnant_topics_count=stagnant_cnt,
        regressed_topics_count=regressed_cnt,
        average_percentage_point_change=avg_pp,
        comparisons=comparisons,
        explanation=expl,
    )


# ---------------------------------------------------------------------------
# 4. Learning Velocity & Progress
# ---------------------------------------------------------------------------


def get_learning_progress(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
) -> LearningProgressResponseData:
    """Calculate learning velocity and longitudinal progress points from real timestamps."""
    _verify_course_ownership(db, user_id, course_id)

    now = utc_now()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    # 1. Historical Snapshots
    snapshots = db.execute(
        select(TopicMasteryHistory)
        .where(
            TopicMasteryHistory.user_id == user_id,
            TopicMasteryHistory.course_id == course_id,
        )
        .order_by(TopicMasteryHistory.recorded_at.asc())
    ).scalars().all()

    # 2. Velocity calculations
    topics_improved_7d = 0
    topics_improved_30d = 0
    transitions_weak_to_dev = 0
    transitions_dev_to_strong = 0
    mastery_deltas: List[float] = []

    # Group snapshots by topic
    topic_snapshots: Dict[uuid.UUID, List[TopicMasteryHistory]] = defaultdict(list)
    for s in snapshots:
        topic_snapshots[s.topic_id].append(s)

    for topic_id, snaps in topic_snapshots.items():
        if len(snaps) < 2:
            continue

        first_snap = snaps[0]
        latest_snap = snaps[-1]
        overall_delta = latest_snap.mastery_score - first_snap.mastery_score
        mastery_deltas.append(overall_delta)

        # Graduations
        if first_snap.mastery_score < DEVELOPING_THRESHOLD and latest_snap.mastery_score >= DEVELOPING_THRESHOLD:
            transitions_weak_to_dev += 1
        if first_snap.mastery_score < STRONG_THRESHOLD and latest_snap.mastery_score >= STRONG_THRESHOLD:
            transitions_dev_to_strong += 1

        # 7d / 30d improvement
        snaps_7d = [s for s in snaps if _as_utc(s.recorded_at) >= seven_days_ago]
        if snaps_7d and snaps_7d[-1].mastery_score > snaps_7d[0].mastery_score:
            topics_improved_7d += 1

        snaps_30d = [s for s in snaps if _as_utc(s.recorded_at) >= thirty_days_ago]
        if snaps_30d and snaps_30d[-1].mastery_score > snaps_30d[0].mastery_score:
            topics_improved_30d += 1

    avg_change = (
        round((sum(mastery_deltas) / len(mastery_deltas)) * 100.0, 1)
        if mastery_deltas
        else None
    )

    if topics_improved_7d >= 3 or (avg_change and avg_change >= 20.0):
        velocity_status = "ACCELERATING"
        velocity_desc = "Strong pace of learning: topics showing rapid upward mastery momentum."
    elif topics_improved_7d >= 1 or topics_improved_30d >= 2:
        velocity_status = "STEADY"
        velocity_desc = "Consistent progress: topics steadily improving over recent study cycles."
    elif len(snapshots) > 0:
        velocity_status = "EARLY_STAGE"
        velocity_desc = "Initial assessment data recorded. Continue tutor sessions to build velocity."
    else:
        velocity_status = "NEEDS_PRACTICE"
        velocity_desc = "Insufficient historical evidence. Complete learning sessions to track velocity."

    velocity = LearningVelocityData(
        topics_improved_7d=topics_improved_7d,
        topics_improved_30d=topics_improved_30d,
        average_mastery_change=avg_change,
        transitions_weak_to_developing=transitions_weak_to_dev,
        transitions_developing_to_strong=transitions_dev_to_strong,
        velocity_status=velocity_status,
        velocity_description=velocity_desc,
    )

    # 3. Longitudinal Progress Points (Grouped by Date)
    date_snapshots: Dict[str, List[float]] = defaultdict(list)
    for s in snapshots:
        d_str = s.recorded_at.strftime("%Y-%m-%d")
        date_snapshots[d_str].append(s.mastery_score)

    history_points: List[LearningProgressPoint] = []
    for d_str in sorted(date_snapshots.keys()):
        scores = date_snapshots[d_str]
        avg_m = round((sum(scores) / len(scores)) * 100.0, 1)
        history_points.append(
            LearningProgressPoint(
                date=d_str,
                average_mastery=avg_m,
                assessed_topics_count=len(scores),
            )
        )

    return LearningProgressResponseData(
        history_points=history_points,
        velocity=velocity,
    )


# ---------------------------------------------------------------------------
# 5. Study Consistency
# ---------------------------------------------------------------------------


def get_study_consistency(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
) -> StudyConsistencyResponseData:
    """Calculate actual study consistency, completed sessions, and streak from real records."""
    _verify_course_ownership(db, user_id, course_id)

    # 1. Fetch study plan items for this user & course
    plan_items = db.execute(
        select(PlanItem)
        .join(StudyPlan, PlanItem.plan_id == StudyPlan.id)
        .where(
            StudyPlan.user_id == user_id,
            StudyPlan.course_id == course_id,
        )
    ).scalars().all()

    completed_cnt = 0
    skipped_cnt = 0
    pending_cnt = 0
    total_scheduled = len(plan_items)

    for item in plan_items:
        st = item.status.upper()
        if st == "COMPLETED":
            completed_cnt += 1
        elif st == "SKIPPED":
            skipped_cnt += 1
        else:
            pending_cnt += 1

    completion_rate = (
        round((completed_cnt / total_scheduled) * 100.0, 1)
        if total_scheduled > 0
        else 0.0
    )

    # 2. Daily Activity Aggregation (actual study sessions + verified practice attempts)
    daily_map: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"completed_sessions": 0, "practice_attempts": 0, "minutes_spent": 0}
    )

    for item in plan_items:
        if item.status.upper() == "COMPLETED" and item.completed_at:
            d_str = item.completed_at.strftime("%Y-%m-%d")
            daily_map[d_str]["completed_sessions"] += 1
            daily_map[d_str]["minutes_spent"] += item.duration_minutes

    attempts = db.execute(
        select(Attempt).where(
            Attempt.user_id == user_id,
            Attempt.course_id == course_id,
        )
    ).scalars().all()

    for a in attempts:
        d_str = a.created_at.strftime("%Y-%m-%d")
        daily_map[d_str]["practice_attempts"] += 1
        # Add approximate time taken in minutes if logged
        if a.time_taken > 0:
            daily_map[d_str]["minutes_spent"] += max(1, a.time_taken // 60)

    # Build DailyActivityPoint list (sorted chronologically)
    daily_activity: List[DailyActivityPoint] = []
    active_days_set: Set[date] = set()

    for d_str in sorted(daily_map.keys()):
        data = daily_map[d_str]
        daily_activity.append(
            DailyActivityPoint(
                date=d_str,
                completed_sessions=data["completed_sessions"],
                practice_attempts=data["practice_attempts"],
                minutes_spent=data["minutes_spent"],
            )
        )
        try:
            active_days_set.add(datetime.strptime(d_str, "%Y-%m-%d").date())
        except ValueError:
            pass

    active_study_days = len(active_days_set)

    # 3. Honest Consecutive Streak Calculation
    # A streak is unbroken consecutive calendar days leading up to today (or yesterday if today is in progress)
    current_streak = 0
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Streak must anchor at today or yesterday
    if today in active_days_set:
        check_date = today
    elif yesterday in active_days_set:
        check_date = yesterday
    else:
        check_date = None

    if check_date:
        while check_date in active_days_set:
            current_streak += 1
            check_date = check_date - timedelta(days=1)

    if current_streak >= 5:
        streak_desc = f"{current_streak}-day study streak! Outstanding learning discipline."
    elif current_streak >= 2:
        streak_desc = f"{current_streak}-day study streak. Great job keeping the momentum."
    elif current_streak == 1:
        streak_desc = "Active study recorded today! Return tomorrow to build a streak."
    else:
        streak_desc = "No active streak. Complete a study session or tutor practice today to start one."

    return StudyConsistencyResponseData(
        completed_sessions=completed_cnt,
        skipped_sessions=skipped_cnt,
        pending_sessions=pending_cnt,
        total_scheduled=total_scheduled,
        completion_rate=completion_rate,
        active_study_days=active_study_days,
        current_streak_days=current_streak,
        daily_activity=daily_activity,
        streak_description=streak_desc,
    )


# ---------------------------------------------------------------------------
# 6. Prerequisite Bottlenecks
# ---------------------------------------------------------------------------


def get_prerequisite_blockers(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
) -> List[PrerequisiteBlockerItem]:
    """Identify weak foundational concepts blocking dependent topics in the knowledge graph."""
    _verify_course_ownership(db, user_id, course_id)

    topics = db.execute(
        select(Topic).where(Topic.course_id == course_id)
    ).scalars().all()
    topic_map = {t.id: t for t in topics}

    if not topics:
        return []

    # Masteries
    masteries = db.execute(
        select(TopicMastery).where(
            TopicMastery.user_id == user_id,
            TopicMastery.topic_id.in_(list(topic_map.keys())),
        )
    ).scalars().all()
    mastery_map = {m.topic_id: m.mastery_score for m in masteries}

    # Prerequisites graph
    prereqs = db.execute(
        select(TopicPrerequisite).where(
            TopicPrerequisite.topic_id.in_(list(topic_map.keys())),
            TopicPrerequisite.prerequisite_id.in_(list(topic_map.keys())),
        )
    ).scalars().all()

    # Dependents: which topics depend on topic_id?
    dependents_map: Dict[uuid.UUID, List[uuid.UUID]] = defaultdict(list)
    for p in prereqs:
        dependents_map[p.prerequisite_id].append(p.topic_id)

    blockers: List[PrerequisiteBlockerItem] = []

    for t in topics:
        dep_ids = dependents_map.get(t.id, [])
        if not dep_ids:
            continue  # Not a prerequisite to anything

        score = mastery_map.get(t.id)
        # Bottleneck condition: topic has multiple dependents AND (is unassessed OR weak)
        if score is None or score < DEVELOPING_THRESHOLD:
            mastery_val = score if score is not None else 0.0
            impact = round(len(dep_ids) * (1.0 - mastery_val) * 10.0, 1)

            blocked_names = [topic_map[did].name for did in dep_ids if did in topic_map]

            if score is None:
                expl = (
                    f"'{t.name}' is unassessed and is a direct prerequisite to {len(dep_ids)} "
                    f"topic(s): {', '.join(blocked_names[:3])}. Assess this topic to unblock learning."
                )
            else:
                expl = (
                    f"'{t.name}' is weak ({round(score * 100)}% mastery) and directly blocks {len(dep_ids)} "
                    f"downstream concept(s): {', '.join(blocked_names[:3])}. Master this concept first."
                )

            blockers.append(
                PrerequisiteBlockerItem(
                    topic_id=t.id,
                    topic_name=t.name,
                    unit_name=t.unit_name,
                    mastery_score=score,
                    mastery_percentage=round(score * 100.0, 1) if score is not None else None,
                    dependent_topics_count=len(dep_ids),
                    blocked_topics_names=blocked_names,
                    bottleneck_impact_score=impact,
                    explanation=expl,
                    action_url=f"/courses/{course_id}/topics/{t.id}/tutor",
                )
            )

    # Sort descending by bottleneck impact score
    blockers.sort(key=lambda b: b.bottleneck_impact_score, reverse=True)
    return blockers


# ---------------------------------------------------------------------------
# 7. Recommendations Engine
# ---------------------------------------------------------------------------


def get_recommended_next_actions(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
) -> List[RecommendationItem]:
    """Generate prioritized, explainable study recommendations using real student data."""
    course = _verify_course_ownership(db, user_id, course_id)

    recommendations: List[RecommendationItem] = []

    # 1. High-Impact Prerequisite Bottlenecks
    blockers = get_prerequisite_blockers(db, user_id, course_id)
    for b in blockers[:2]:
        recommendations.append(
            RecommendationItem(
                id=f"rec-bottleneck-{b.topic_id}",
                title=f"Resolve Foundational Bottleneck: {b.topic_name}",
                description=f"Master {b.topic_name} to unblock {b.dependent_topics_count} dependent topic(s) ({', '.join(b.blocked_topics_names[:2])}).",
                reason=b.explanation,
                priority="HIGH",
                action_type="TUTOR",
                action_url=b.action_url,
                related_topic_id=b.topic_id,
                supporting_evidence=f"Blocks {b.dependent_topics_count} downstream topics with impact score {b.bottleneck_impact_score}.",
            )
        )

    # 2. Developing Topics Near Mastery (50-79%)
    mastery_analytics = get_topic_mastery_analytics(db, user_id, course_id)
    developing_topics = [
        t for t in mastery_analytics.topics
        if t.learning_status == "DEVELOPING" and t.mastery_score and t.mastery_score >= 0.60
    ]
    if developing_topics:
        t_dev = developing_topics[0]
        recommendations.append(
            RecommendationItem(
                id=f"rec-developing-{t_dev.topic_id}",
                title=f"Push to Strong Mastery: {t_dev.topic_name}",
                description=f"You are at {t_dev.mastery_percentage}% on {t_dev.topic_name}. A few verified practice problems will graduate this to STRONG.",
                reason="High-yield recovery: topic has established foundational grasp and is close to the 80% mastery threshold.",
                priority="MEDIUM",
                action_type="PRACTICE",
                action_url=f"/courses/{course_id}/topics/{t_dev.topic_id}/tutor",
                related_topic_id=t_dev.topic_id,
                supporting_evidence=f"Current mastery is {t_dev.mastery_percentage}% across {t_dev.evidence_count} attempt(s).",
            )
        )

    # 3. Unassessed Topics
    unassessed_topics = [t for t in mastery_analytics.topics if t.learning_status == "NOT_ASSESSED"]
    if unassessed_topics:
        t_un = unassessed_topics[0]
        recommendations.append(
            RecommendationItem(
                id=f"rec-unassessed-{t_un.topic_id}",
                title=f"Calibrate Topic Knowledge: {t_un.topic_name}",
                description=f"Complete a quick diagnostic on {t_un.topic_name} to establish baseline mastery and identify any hidden gaps.",
                reason="Missing evidence: unassessed topics limit the accuracy of your exam readiness score.",
                priority="MEDIUM",
                action_type="DIAGNOSTIC",
                action_url=f"/courses/{course_id}/diagnostic",
                related_topic_id=t_un.topic_id,
                supporting_evidence="Zero assessment attempts recorded for this topic.",
            )
        )

    # 4. Approaching Exam Date Warning
    if course.exam_date:
        days_left = (course.exam_date - date.today()).days
        if 0 <= days_left <= 14:
            recommendations.append(
                RecommendationItem(
                    id="rec-exam-countdown",
                    title=f"Targeted Exam Preparation: {days_left} Days Left",
                    description=f"Your exam is in {days_left} day(s). Prioritize active study plan sessions and high-priority weak topics.",
                    reason="Upcoming exam date constraint.",
                    priority="HIGH",
                    action_type="STUDY_PLAN",
                    action_url=f"/courses/{course_id}/study-plan",
                    related_topic_id=None,
                    supporting_evidence=f"Exam scheduled for {course.exam_date.isoformat()}.",
                )
            )

    # 5. Pending Study Plan Sessions
    overview = get_course_overview(db, user_id, course_id)
    if overview.pending_study_sessions > 0 and overview.active_plan_id:
        recommendations.append(
            RecommendationItem(
                id="rec-study-plan-pending",
                title="Continue Active Study Roadmap",
                description=f"You have {overview.pending_study_sessions} scheduled study session(s) pending in your active learning plan.",
                reason="Staying on track with daily scheduled sessions maintains study consistency.",
                priority="LOW",
                action_type="STUDY_PLAN",
                action_url=f"/courses/{course_id}/study-plan",
                related_topic_id=None,
                supporting_evidence=f"{overview.completed_study_sessions} sessions completed out of {overview.completed_study_sessions + overview.pending_study_sessions}.",
            )
        )

    return recommendations


# ---------------------------------------------------------------------------
# 8. Full Analytics Dashboard Aggregate
# ---------------------------------------------------------------------------


def get_full_dashboard(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
) -> FullAnalyticsDashboardResponseData:
    """Retrieve complete learning analytics dashboard for a course in one call."""
    overview = get_course_overview(db, user_id, course_id)
    mastery_analytics = get_topic_mastery_analytics(db, user_id, course_id)
    improvement = get_diagnostic_comparison(db, user_id, course_id)
    progress = get_learning_progress(db, user_id, course_id)
    consistency = get_study_consistency(db, user_id, course_id)
    exam_readiness = calculate_exam_readiness(db, user_id, course_id)
    bottlenecks = get_prerequisite_blockers(db, user_id, course_id)
    recommendations = get_recommended_next_actions(db, user_id, course_id)

    return FullAnalyticsDashboardResponseData(
        overview=overview,
        mastery_analytics=mastery_analytics,
        improvement=improvement,
        progress=progress,
        consistency=consistency,
        exam_readiness=exam_readiness,
        bottlenecks=bottlenecks,
        recommendations=recommendations,
    )
