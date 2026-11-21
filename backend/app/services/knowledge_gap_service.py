"""Service for Knowledge Gap Analysis and Prerequisite Intelligence."""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import uuid

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.ai.llm import (
    LLMError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
    generate_completion,
)
from app.core.database import utc_now
from app.models.attempt import Attempt
from app.models.course import Course
from app.models.diagnostic_session import DiagnosticSession
from app.models.knowledge_gap import KnowledgeGap, KnowledgeGapAnalysis
from app.models.topic import Topic
from app.models.topic_prerequisite import TopicPrerequisite
from app.schemas.diagnostic import DiagnosticQuestionsResponse, DiagnosticStartRequest, QuestionPublicResponse
from app.schemas.knowledge_gap import (
    GapRecommendationItem,
    KnowledgeGapAnalysisResponseData,
    KnowledgeGapDetail,
    KnowledgeGapHistoryItem,
    PrerequisiteNode,
    TopicPerformanceMetric,
)
from app.services.diagnostic_service import (
    CourseNotFoundError,
    DiagnosticError,
    start_diagnostic_session,
)

logger = logging.getLogger(__name__)

PROMPT_FILE_PATH = (
    Path(__file__).resolve().parents[1] / "agents" / "prompts" / "knowledge_gap_prompt.txt"
)

# Configurable classification thresholds
STRONG_THRESHOLD = 80.0
DEVELOPING_THRESHOLD = 50.0
MINIMUM_EVIDENCE_ATTEMPTS = 3


class KnowledgeGapError(Exception):
    """Base exception for knowledge gap analysis operations."""


class AnalysisNotFoundError(KnowledgeGapError):
    """Raised when an analysis record is not found."""


def load_knowledge_gap_prompt() -> str:
    """Load academic knowledge gap explanation prompt from disk."""
    if not PROMPT_FILE_PATH.exists():
        logger.warning(
            "Knowledge gap prompt not found at %s; using embedded fallback.", PROMPT_FILE_PATH
        )
        return (
            "You are an academic learning analyst. Explain the student's evaluated knowledge "
            "gaps and recommend prioritized prerequisite revision in strictly valid JSON format."
        )
    return PROMPT_FILE_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Topic Performance Calculation
# ---------------------------------------------------------------------------


def get_topic_performance(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
) -> Dict[uuid.UUID, TopicPerformanceMetric]:
    """Calculate diagnostic performance indicators for every topic in the course."""
    # Retrieve all course topics
    topics = list(
        db.execute(
            select(Topic)
            .where(Topic.course_id == course_id)
            .order_by(Topic.created_at, Topic.name)
        ).scalars().all()
    )

    if not topics:
        return {}

    # Query all attempts for user in this course
    attempts = list(
        db.execute(
            select(Attempt)
            .where(Attempt.user_id == user_id, Attempt.course_id == course_id)
        ).scalars().all()
    )

    # Group attempts by topic_id
    attempts_by_topic: Dict[uuid.UUID, List[Attempt]] = defaultdict(list)
    for att in attempts:
        attempts_by_topic[att.topic_id].append(att)

    metrics: Dict[uuid.UUID, TopicPerformanceMetric] = {}

    for topic in topics:
        topic_attempts = attempts_by_topic.get(topic.id, [])
        total_attempts = len(topic_attempts)
        correct_attempts = sum(1 for a in topic_attempts if a.is_correct)

        if total_attempts > 0:
            accuracy = round((correct_attempts / total_attempts) * 100.0, 1)
            last_attempt_time = max(a.created_at for a in topic_attempts)
            # Base confidence based on sample size
            if total_attempts >= MINIMUM_EVIDENCE_ATTEMPTS:
                base_conf = 1.0
            elif total_attempts == 2:
                base_conf = 0.75
            else:
                base_conf = 0.5
        else:
            accuracy = 0.0
            last_attempt_time = None
            base_conf = 0.0

        # Classify topic knowledge
        if total_attempts == 0:
            status = "not_assessed"
        elif accuracy >= STRONG_THRESHOLD:
            status = "strong"
        elif accuracy >= DEVELOPING_THRESHOLD:
            status = "developing"
        else:
            status = "weak"

        metrics[topic.id] = TopicPerformanceMetric(
            topic_id=topic.id,
            topic_name=topic.name,
            total_attempts=total_attempts,
            correct_attempts=correct_attempts,
            accuracy_percentage=accuracy,
            knowledge_status=status,
            confidence_score=base_conf,
            last_attempted_at=last_attempt_time,
            unit_name=topic.unit_name,
        )

    return metrics


def classify_topic_knowledge(performance: TopicPerformanceMetric) -> str:
    """Classify knowledge state based on accuracy and attempt count."""
    return performance.knowledge_status


def find_weak_topics(
    performances: Dict[uuid.UUID, TopicPerformanceMetric],
) -> List[TopicPerformanceMetric]:
    """Extract weak or struggling topics needing intervention."""
    return [
        p for p in performances.values()
        if p.knowledge_status == "weak"
    ]


# ---------------------------------------------------------------------------
# 2. Prerequisite Intelligence & Traversal
# ---------------------------------------------------------------------------


def build_course_prerequisite_maps(
    db: Session,
    course_id: uuid.UUID,
) -> Tuple[Dict[uuid.UUID, List[uuid.UUID]], Dict[uuid.UUID, List[uuid.UUID]]]:
    """Build directed prerequisite adjacency maps within the course scope.

    Returns:
        (prereqs_of_topic, dependents_of_topic)
        - prereqs_of_topic[topic_id] = [direct_prereq_id_1, direct_prereq_id_2, ...]
        - dependents_of_topic[topic_id] = [dependent_id_1, dependent_id_2, ...]
    """
    edges = list(
        db.execute(
            select(TopicPrerequisite)
            .join(Topic, Topic.id == TopicPrerequisite.topic_id)
            .where(Topic.course_id == course_id)
        ).scalars().all()
    )

    prereqs_of: Dict[uuid.UUID, List[uuid.UUID]] = defaultdict(list)
    dependents_of: Dict[uuid.UUID, List[uuid.UUID]] = defaultdict(list)

    for edge in edges:
        # edge: topic_id requires prerequisite_id
        prereqs_of[edge.topic_id].append(edge.prerequisite_id)
        dependents_of[edge.prerequisite_id].append(edge.topic_id)

    return prereqs_of, dependents_of


def trace_prerequisite_chain(
    target_topic_id: uuid.UUID,
    prereqs_map: Dict[uuid.UUID, List[uuid.UUID]],
    performances: Dict[uuid.UUID, TopicPerformanceMetric],
    max_depth: int = 10,
) -> List[PrerequisiteNode]:
    """Traverse all direct and indirect prerequisites of target topic via BFS.

    Returns ordered list of PrerequisiteNode from immediate prerequisites to deep roots.
    """
    visited: Set[uuid.UUID] = {target_topic_id}
    queue: deque[Tuple[uuid.UUID, int, bool]] = deque()

    # Seed direct prerequisites
    for p_id in prereqs_map.get(target_topic_id, []):
        if p_id not in visited and p_id in performances:
            visited.add(p_id)
            queue.append((p_id, 1, True))

    chain: List[PrerequisiteNode] = []

    while queue:
        curr_id, depth, is_direct = queue.popleft()
        perf = performances[curr_id]

        chain.append(
            PrerequisiteNode(
                topic_id=curr_id,
                topic_name=perf.topic_name,
                knowledge_status=perf.knowledge_status,
                accuracy_percentage=perf.accuracy_percentage,
                depth=depth,
                is_direct=is_direct,
            )
        )

        if depth < max_depth:
            for next_p_id in prereqs_map.get(curr_id, []):
                if next_p_id not in visited and next_p_id in performances:
                    visited.add(next_p_id)
                    queue.append((next_p_id, depth + 1, False))

    return chain


def count_downstream_dependents(
    topic_id: uuid.UUID,
    dependents_map: Dict[uuid.UUID, List[uuid.UUID]],
) -> int:
    """Count all direct and transitive downstream topics dependent on this topic."""
    visited: Set[uuid.UUID] = {topic_id}
    queue = deque([topic_id])
    count = 0

    while queue:
        curr = queue.popleft()
        for dep in dependents_map.get(curr, []):
            if dep not in visited:
                visited.add(dep)
                count += 1
                queue.append(dep)

    return count


# ---------------------------------------------------------------------------
# 3. Gap Severity & Confidence Calculation
# ---------------------------------------------------------------------------


def calculate_gap_severity(
    target_metric: TopicPerformanceMetric,
    prereq_chain: List[PrerequisiteNode],
    dependents_count: int = 0,
) -> float:
    """Calculate deterministic gap severity score on 0 to 100 scale.

    Formula:
        Severity = 0.50 * Target_Weakness + 0.30 * Prerequisite_Weakness + 0.20 * Topic_Importance
    """
    # 1. Target weakness (100 - accuracy)
    target_weakness = max(0.0, 100.0 - target_metric.accuracy_percentage)

    # 2. Prerequisite weakness
    assessed_prereqs = [p for p in prereq_chain if p.knowledge_status != "not_assessed"]
    if assessed_prereqs:
        avg_prereq_weakness = sum(
            max(0.0, 100.0 - p.accuracy_percentage) for p in assessed_prereqs
        ) / len(assessed_prereqs)
    else:
        # If no prerequisites exist or none assessed, default to 0.0 weakness contribution
        avg_prereq_weakness = 0.0

    # 3. Topic structural importance (base 40 + bonus for downstream dependents)
    topic_importance = min(100.0, 40.0 + (dependents_count * 15.0))

    severity = (0.50 * target_weakness) + (0.30 * avg_prereq_weakness) + (0.20 * topic_importance)
    return round(min(100.0, max(0.0, severity)), 1)


def calculate_confidence(
    target_metric: TopicPerformanceMetric,
    prereq_chain: List[PrerequisiteNode],
) -> float:
    """Calculate analysis confidence (0.0 to 1.0) based on sample size and unassessed prerequisites."""
    base_conf = target_metric.confidence_score

    # Penalty for unassessed prerequisites
    unassessed_count = sum(1 for p in prereq_chain if p.knowledge_status == "not_assessed")
    penalty = unassessed_count * 0.15

    final_conf = max(0.2, base_conf - penalty) if target_metric.total_attempts > 0 else 0.0
    return round(min(1.0, max(0.0, final_conf)), 2)


# ---------------------------------------------------------------------------
# 4. Foundational Gap Classification
# ---------------------------------------------------------------------------


def classify_knowledge_gap(
    target_metric: TopicPerformanceMetric,
    prereq_chain: List[PrerequisiteNode],
) -> Tuple[str, Dict[str, Any]]:
    """Determine the causal classification and evidence for a struggling topic.

    Classifications:
        - foundational_weakness: Target is weak and 1+ prerequisites are also weak.
        - potential_knowledge_gap: Target is weak and 1+ prerequisites are unassessed.
        - isolated_difficulty: Target is weak despite strong prerequisite performance.
        - direct_weakness: Target has poor performance and no prerequisites, or general weakness.
    """
    if not prereq_chain:
        evidence = {
            "target_accuracy": target_metric.accuracy_percentage,
            "prerequisites_count": 0,
            "explanation": f"{target_metric.topic_name} has no designated prerequisite topics in this course.",
        }
        return "direct_weakness", evidence

    weak_prereqs = [p for p in prereq_chain if p.knowledge_status == "weak"]
    unassessed_prereqs = [p for p in prereq_chain if p.knowledge_status == "not_assessed"]
    strong_prereqs = [p for p in prereq_chain if p.knowledge_status == "strong"]

    evidence = {
        "target_accuracy": target_metric.accuracy_percentage,
        "total_prerequisites": len(prereq_chain),
        "weak_prerequisites": [p.topic_name for p in weak_prereqs],
        "unassessed_prerequisites": [p.topic_name for p in unassessed_prereqs],
        "strong_prerequisites": [p.topic_name for p in strong_prereqs],
    }

    # 1. Foundational weakness: 1+ prerequisites are also weak
    if weak_prereqs:
        evidence["bottlenecks"] = [p.topic_name for p in weak_prereqs]
        return "foundational_weakness", evidence

    # 2. Potential knowledge gap: 1+ prerequisites have never been assessed
    if unassessed_prereqs:
        evidence["missing_evidence"] = [p.topic_name for p in unassessed_prereqs]
        return "potential_knowledge_gap", evidence

    # 3. Isolated difficulty: target is weak despite all prerequisites being strong
    if len(strong_prereqs) == len(prereq_chain):
        return "isolated_difficulty", evidence

    # 4. Direct weakness
    return "direct_weakness", evidence


# ---------------------------------------------------------------------------
# 5. Recommendation Generation
# ---------------------------------------------------------------------------


def generate_recommendations(
    gaps: List[KnowledgeGapDetail],
    performances: Dict[uuid.UUID, TopicPerformanceMetric],
) -> List[GapRecommendationItem]:
    """Generate prioritized, deduplicated learning recommendations based on gap analysis."""
    recommendations: List[GapRecommendationItem] = []
    seen_topics: Set[uuid.UUID] = set()
    priority = 1

    # Sort gaps by severity descending
    sorted_gaps = sorted(gaps, key=lambda g: g.severity, reverse=True)

    for gap in sorted_gaps:
        if gap.gap_type == "foundational_weakness":
            # Recommend revising the weakest prerequisite first
            weak_prereqs = [
                p for p in gap.prerequisite_chain
                if p.knowledge_status == "weak" and p.topic_id not in seen_topics
            ]
            # Sort weakest first
            weak_prereqs.sort(key=lambda p: p.accuracy_percentage)
            for p in weak_prereqs:
                seen_topics.add(p.topic_id)
                recommendations.append(
                    GapRecommendationItem(
                        priority=priority,
                        topic_id=p.topic_id,
                        topic_name=p.topic_name,
                        action_type="revise_prerequisite",
                        reason=f"Foundational requirement for {gap.topic_name}. Strengthening this topic will directly unblock advanced concepts.",
                        severity=gap.severity,
                    )
                )
                priority += 1

        elif gap.gap_type == "potential_knowledge_gap":
            # Recommend diagnostic reassessment of unassessed prerequisites
            unassessed = [
                p for p in gap.prerequisite_chain
                if p.knowledge_status == "not_assessed" and p.topic_id not in seen_topics
            ]
            for p in unassessed:
                seen_topics.add(p.topic_id)
                recommendations.append(
                    GapRecommendationItem(
                        priority=priority,
                        topic_id=p.topic_id,
                        topic_name=p.topic_name,
                        action_type="take_diagnostic",
                        reason=f"Unassessed prerequisite for {gap.topic_name}. Take a targeted check to determine if prerequisite gaps exist.",
                        severity=gap.severity,
                    )
                )
                priority += 1

        # Target topic practice recommendation
        if gap.topic_id not in seen_topics:
            seen_topics.add(gap.topic_id)
            if gap.gap_type == "isolated_difficulty":
                reason = f"Prerequisites are solid ({gap.evidence.get('strong_prerequisites', [])}). Focus on problem variations and edge cases specific to {gap.topic_name}."
            else:
                reason = f"Directly practice concept applications and core patterns for {gap.topic_name}."

            recommendations.append(
                GapRecommendationItem(
                    priority=priority,
                    topic_id=gap.topic_id,
                    topic_name=gap.topic_name,
                    action_type="practice_topic",
                    reason=reason,
                    severity=gap.severity,
                )
            )
            priority += 1

    return recommendations


# ---------------------------------------------------------------------------
# 6. AI Explanation Layer with Deterministic Fallback
# ---------------------------------------------------------------------------


def generate_deterministic_summary(
    gaps: List[KnowledgeGapDetail],
    performances: Dict[uuid.UUID, TopicPerformanceMetric],
) -> str:
    """Fallback generator producing clear academic summaries without LLM."""
    if not gaps:
        assessed = sum(1 for p in performances.values() if p.knowledge_status != "not_assessed")
        if assessed == 0:
            return "No diagnostic assessments have been completed yet. Complete a diagnostic to reveal your topic strengths and knowledge gaps."
        return "Strong foundational knowledge observed across assessed topics. No critical prerequisite gaps detected."

    foundational = [g for g in gaps if g.gap_type == "foundational_weakness"]
    potential = [g for g in gaps if g.gap_type == "potential_knowledge_gap"]
    isolated = [g for g in gaps if g.gap_type == "isolated_difficulty"]

    parts = []
    if foundational:
        topic_names = ", ".join(f"'{g.topic_name}'" for g in foundational[:2])
        parts.append(f"Foundational knowledge gaps detected affecting {topic_names}.")
    if potential:
        topic_names = ", ".join(f"'{g.topic_name}'" for g in potential[:2])
        parts.append(f"Unassessed prerequisite dependencies identified for {topic_names}.")
    if isolated:
        topic_names = ", ".join(f"'{g.topic_name}'" for g in isolated[:2])
        parts.append(f"Targeted practice recommended for {topic_names} as foundational prerequisites are already strong.")

    return " ".join(parts) if parts else f"{len(gaps)} knowledge gap(s) identified requiring structured review."


def generate_ai_explanation(
    gaps: List[KnowledgeGapDetail],
    performances: Dict[uuid.UUID, TopicPerformanceMetric],
    llm_generator: Optional[Callable[..., str]] = None,
) -> str:
    """Generate human-friendly academic explanation using LLM with deterministic fallback."""
    generator = llm_generator or generate_completion

    system_prompt = load_knowledge_gap_prompt()
    gap_summaries = [
        {
            "topic": g.topic_name,
            "accuracy": g.accuracy_percentage,
            "classification": g.gap_type,
            "severity": g.severity,
            "evidence": g.evidence,
        }
        for g in gaps[:5]
    ]

    user_prompt = (
        f"Analyze the following student assessment and prerequisite graph data:\n\n"
        f"Identified Gaps:\n{json.dumps(gap_summaries, indent=2)}\n\n"
        f"Generate supportive, precise academic feedback in strict JSON format."
    )

    try:
        raw_resp = generator(
            prompt=user_prompt,
            system=system_prompt,
            response_format="json",
            temperature=0.2,
        )
        text = raw_resp.strip()
        if text.startswith("```json"):
            text = text[len("```json"):].strip()
        elif text.startswith("```"):
            text = text[len("```"):].strip()
        if text.endswith("```"):
            text = text[:-len("```")].strip()

        parsed = json.loads(text)
        if isinstance(parsed, dict) and "summary" in parsed and parsed["summary"]:
            return str(parsed["summary"]).strip()
    except Exception as exc:
        logger.info("Ollama explanation unavailable or malformed (%s); using deterministic summary.", exc)

    return generate_deterministic_summary(gaps, performances)


# ---------------------------------------------------------------------------
# 7. Analysis Orchestration & Persistence
# ---------------------------------------------------------------------------


def analyze_knowledge_gaps(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
    llm_generator: Optional[Callable[..., str]] = None,
) -> KnowledgeGapAnalysisResponseData:
    """Run full deterministic knowledge gap analysis for a student on a course."""
    # 1. Verify course ownership
    course = db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user_id)
    ).scalar_one_or_none()

    if not course:
        raise CourseNotFoundError("Course not found or access denied.")

    # 2. Get topic performance
    performances = get_topic_performance(db, user_id, course_id)

    # 3. Build prerequisite maps
    prereqs_map, dependents_map = build_course_prerequisite_maps(db, course_id)

    # 4. Find weak and struggling topics
    weak_metrics = find_weak_topics(performances)

    # Also check developing topics that have weak prerequisites
    developing_metrics = [
        p for p in performances.values()
        if p.knowledge_status == "developing"
    ]
    candidate_metrics = list(weak_metrics)

    for dev in developing_metrics:
        chain = trace_prerequisite_chain(dev.topic_id, prereqs_map, performances)
        if any(p.knowledge_status == "weak" for p in chain):
            candidate_metrics.append(dev)

    # 5. Build KnowledgeGap records
    gaps: List[KnowledgeGapDetail] = []

    for metric in candidate_metrics:
        prereq_chain = trace_prerequisite_chain(metric.topic_id, prereqs_map, performances)
        dep_count = count_downstream_dependents(metric.topic_id, dependents_map)

        gap_type, evidence = classify_knowledge_gap(metric, prereq_chain)
        severity = calculate_gap_severity(metric, prereq_chain, dep_count)
        confidence = calculate_confidence(metric, prereq_chain)

        # Generate recommendation text
        if gap_type == "foundational_weakness":
            bottlenecks = evidence.get("weak_prerequisites", [])
            rec = f"Revise foundational prerequisites ({', '.join(bottlenecks)}) before re-attempting {metric.topic_name}."
        elif gap_type == "potential_knowledge_gap":
            missing = evidence.get("unassessed_prerequisites", [])
            rec = f"Complete assessment for unassessed prerequisites ({', '.join(missing)}) to confirm foundational competency."
        elif gap_type == "isolated_difficulty":
            rec = f"Foundational knowledge is strong. Focus on topic-specific problem patterns and edge cases for {metric.topic_name}."
        else:
            rec = f"Practice core conceptual problems for {metric.topic_name}."

        gaps.append(
            KnowledgeGapDetail(
                id=uuid.uuid4(),
                topic_id=metric.topic_id,
                topic_name=metric.topic_name,
                gap_type=gap_type,  # type: ignore[arg-type]
                severity=severity,
                confidence=confidence,
                accuracy_percentage=metric.accuracy_percentage,
                attempt_count=metric.total_attempts,
                evidence=evidence,
                recommendation=rec,
                prerequisite_chain=prereq_chain,
            )
        )

    # Sort gaps by severity descending
    gaps.sort(key=lambda g: g.severity, reverse=True)

    # 6. Generate recommendations
    recommendations = generate_recommendations(gaps, performances)

    # 7. Calculate overall course gap score (0 to 100)
    if gaps:
        overall_gap_score = round(sum(g.severity for g in gaps) / len(gaps), 1)
    else:
        overall_gap_score = 0.0

    # 8. AI / Deterministic Explanation
    summary = generate_ai_explanation(gaps, performances, llm_generator=llm_generator)

    # 9. Get latest diagnostic session id if any
    latest_session = db.execute(
        select(DiagnosticSession)
        .where(DiagnosticSession.course_id == course_id, DiagnosticSession.user_id == user_id)
        .order_by(DiagnosticSession.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    # 10. Persist analysis & individual gaps inside database transaction
    analysis_record = KnowledgeGapAnalysis(
        user_id=user_id,
        course_id=course_id,
        diagnostic_session_id=latest_session.id if latest_session else None,
        overall_gap_score=overall_gap_score,
        status="completed",
        analysis_data={
            "summary": summary,
            "overall_gap_score": overall_gap_score,
            "total_topics": len(performances),
            "assessed_topics": sum(1 for p in performances.values() if p.knowledge_status != "not_assessed"),
            "strong_topics_count": sum(1 for p in performances.values() if p.knowledge_status == "strong"),
            "developing_topics_count": sum(1 for p in performances.values() if p.knowledge_status == "developing"),
            "weak_topics_count": sum(1 for p in performances.values() if p.knowledge_status == "weak"),
            "unassessed_topics_count": sum(1 for p in performances.values() if p.knowledge_status == "not_assessed"),
        },
    )
    db.add(analysis_record)
    db.flush()

    for gap in gaps:
        gap_obj = KnowledgeGap(
            id=gap.id,
            analysis_id=analysis_record.id,
            topic_id=gap.topic_id,
            gap_type=gap.gap_type,
            severity=gap.severity,
            confidence=gap.confidence,
            evidence=gap.evidence,
            recommendation=gap.recommendation,
        )
        db.add(gap_obj)

    db.commit()
    db.refresh(analysis_record)

    # Format return data
    return KnowledgeGapAnalysisResponseData(
        analysis_id=analysis_record.id,
        course_id=course_id,
        diagnostic_session_id=analysis_record.diagnostic_session_id,
        status=analysis_record.status,
        overall_gap_score=overall_gap_score,
        created_at=analysis_record.created_at,
        summary=summary,
        total_topics=len(performances),
        assessed_topics=sum(1 for p in performances.values() if p.knowledge_status != "not_assessed"),
        strong_topics_count=sum(1 for p in performances.values() if p.knowledge_status == "strong"),
        developing_topics_count=sum(1 for p in performances.values() if p.knowledge_status == "developing"),
        weak_topics_count=sum(1 for p in performances.values() if p.knowledge_status == "weak"),
        unassessed_topics_count=sum(1 for p in performances.values() if p.knowledge_status == "not_assessed"),
        topic_performances=list(performances.values()),
        gaps=gaps,
        recommendations=recommendations,
    )


def get_latest_knowledge_gap_analysis(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
) -> Optional[KnowledgeGapAnalysisResponseData]:
    """Retrieve the most recent saved knowledge gap analysis for a course."""
    analysis = db.execute(
        select(KnowledgeGapAnalysis)
        .where(
            KnowledgeGapAnalysis.course_id == course_id,
            KnowledgeGapAnalysis.user_id == user_id,
        )
        .options(
            selectinload(KnowledgeGapAnalysis.gaps).selectinload(KnowledgeGap.topic)
        )
        .order_by(KnowledgeGapAnalysis.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    if not analysis:
        return None

    performances = get_topic_performance(db, user_id, course_id)
    prereqs_map, _ = build_course_prerequisite_maps(db, course_id)

    gaps: List[KnowledgeGapDetail] = []
    for g in analysis.gaps:
        prereq_chain = trace_prerequisite_chain(g.topic_id, prereqs_map, performances)
        t_perf = performances.get(g.topic_id)
        gaps.append(
            KnowledgeGapDetail(
                id=g.id,
                topic_id=g.topic_id,
                topic_name=g.topic.name if g.topic else "Unknown Topic",
                gap_type=g.gap_type,  # type: ignore[arg-type]
                severity=g.severity,
                confidence=g.confidence,
                accuracy_percentage=t_perf.accuracy_percentage if t_perf else 0.0,
                attempt_count=t_perf.total_attempts if t_perf else 0,
                evidence=g.evidence or {},
                recommendation=g.recommendation,
                prerequisite_chain=prereq_chain,
            )
        )

    recommendations = generate_recommendations(gaps, performances)

    return KnowledgeGapAnalysisResponseData(
        analysis_id=analysis.id,
        course_id=course_id,
        diagnostic_session_id=analysis.diagnostic_session_id,
        status=analysis.status,
        overall_gap_score=analysis.overall_gap_score,
        created_at=analysis.created_at,
        summary=analysis.analysis_data.get("summary", "Knowledge gap analysis completed."),
        total_topics=len(performances),
        assessed_topics=sum(1 for p in performances.values() if p.knowledge_status != "not_assessed"),
        strong_topics_count=sum(1 for p in performances.values() if p.knowledge_status == "strong"),
        developing_topics_count=sum(1 for p in performances.values() if p.knowledge_status == "developing"),
        weak_topics_count=sum(1 for p in performances.values() if p.knowledge_status == "weak"),
        unassessed_topics_count=sum(1 for p in performances.values() if p.knowledge_status == "not_assessed"),
        topic_performances=list(performances.values()),
        gaps=gaps,
        recommendations=recommendations,
    )


def get_knowledge_gap_history(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
) -> List[KnowledgeGapHistoryItem]:
    """Retrieve historical knowledge gap analyses for a course."""
    analyses = list(
        db.execute(
            select(KnowledgeGapAnalysis)
            .where(
                KnowledgeGapAnalysis.course_id == course_id,
                KnowledgeGapAnalysis.user_id == user_id,
            )
            .options(selectinload(KnowledgeGapAnalysis.gaps))
            .order_by(KnowledgeGapAnalysis.created_at.desc())
        ).scalars().all()
    )

    return [
        KnowledgeGapHistoryItem(
            analysis_id=a.id,
            course_id=a.course_id,
            overall_gap_score=a.overall_gap_score,
            weak_topics_count=len(a.gaps),
            created_at=a.created_at,
        )
        for a in analyses
    ]


def get_topic_knowledge_gap(
    db: Session,
    user_id: uuid.UUID,
    topic_id: uuid.UUID,
) -> Optional[KnowledgeGapDetail]:
    """Retrieve the most recent knowledge gap evaluation for a specific topic."""
    # Find topic and verify ownership
    topic = db.execute(
        select(Topic)
        .join(Course, Course.id == Topic.course_id)
        .where(Topic.id == topic_id, Course.user_id == user_id)
    ).scalar_one_or_none()

    if not topic:
        return None

    gap_record = db.execute(
        select(KnowledgeGap)
        .join(KnowledgeGapAnalysis, KnowledgeGapAnalysis.id == KnowledgeGap.analysis_id)
        .where(
            KnowledgeGap.topic_id == topic_id,
            KnowledgeGapAnalysis.user_id == user_id,
        )
        .order_by(KnowledgeGap.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    if not gap_record:
        return None

    performances = get_topic_performance(db, user_id, topic.course_id)
    prereqs_map, _ = build_course_prerequisite_maps(db, topic.course_id)
    prereq_chain = trace_prerequisite_chain(topic_id, prereqs_map, performances)
    t_perf = performances.get(topic_id)

    return KnowledgeGapDetail(
        id=gap_record.id,
        topic_id=gap_record.topic_id,
        topic_name=topic.name,
        gap_type=gap_record.gap_type,  # type: ignore[arg-type]
        severity=gap_record.severity,
        confidence=gap_record.confidence,
        accuracy_percentage=t_perf.accuracy_percentage if t_perf else 0.0,
        attempt_count=t_perf.total_attempts if t_perf else 0,
        evidence=gap_record.evidence or {},
        recommendation=gap_record.recommendation,
        prerequisite_chain=prereq_chain,
    )


def get_gap_recommendations(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
) -> List[GapRecommendationItem]:
    """Get prioritized learning recommendations from the latest analysis or on-the-fly."""
    latest = get_latest_knowledge_gap_analysis(db, user_id, course_id)
    if latest:
        return latest.recommendations

    # Compute on the fly if not yet saved
    performances = get_topic_performance(db, user_id, course_id)
    prereqs_map, dependents_map = build_course_prerequisite_maps(db, course_id)
    weak_metrics = find_weak_topics(performances)

    gaps: List[KnowledgeGapDetail] = []
    for metric in weak_metrics:
        prereq_chain = trace_prerequisite_chain(metric.topic_id, prereqs_map, performances)
        dep_count = count_downstream_dependents(metric.topic_id, dependents_map)
        gap_type, evidence = classify_knowledge_gap(metric, prereq_chain)
        severity = calculate_gap_severity(metric, prereq_chain, dep_count)
        confidence = calculate_confidence(metric, prereq_chain)
        gaps.append(
            KnowledgeGapDetail(
                topic_id=metric.topic_id,
                topic_name=metric.topic_name,
                gap_type=gap_type,  # type: ignore[arg-type]
                severity=severity,
                confidence=confidence,
                accuracy_percentage=metric.accuracy_percentage,
                attempt_count=metric.total_attempts,
                evidence=evidence,
                prerequisite_chain=prereq_chain,
            )
        )

    return generate_recommendations(gaps, performances)


def reassess_unassessed_prerequisites(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
    difficulty: str = "mixed",
    questions_per_topic: int = 2,
    llm_generator: Optional[Callable[..., str]] = None,
) -> DiagnosticQuestionsResponse:
    """Launch a targeted diagnostic assessment focusing on unassessed prerequisite topics."""
    performances = get_topic_performance(db, user_id, course_id)
    prereqs_map, _ = build_course_prerequisite_maps(db, course_id)

    # Find unassessed topics that are prerequisites to weak or developing topics
    unassessed_prereq_ids: Set[uuid.UUID] = set()
    for metric in performances.values():
        if metric.knowledge_status in {"weak", "developing"}:
            chain = trace_prerequisite_chain(metric.topic_id, prereqs_map, performances)
            for p in chain:
                if p.knowledge_status == "not_assessed":
                    unassessed_prereq_ids.add(p.topic_id)

    # If no unassessed prerequisites of weak topics exist, select any unassessed topic
    if not unassessed_prereq_ids:
        for metric in performances.values():
            if metric.knowledge_status == "not_assessed":
                unassessed_prereq_ids.add(metric.topic_id)

    if not unassessed_prereq_ids:
        raise KnowledgeGapError("All course topics have already been assessed! No unassessed prerequisites remain.")

    # Re-use Part 7 Diagnostic Engine
    start_payload = DiagnosticStartRequest(
        mode="selected",
        topic_ids=list(unassessed_prereq_ids),
        difficulty=difficulty,  # type: ignore[arg-type]
        questions_per_topic=questions_per_topic,
    )

    session, questions = start_diagnostic_session(
        db=db,
        user_id=user_id,
        course_id=course_id,
        payload=start_payload,
        llm_generator=llm_generator,
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

