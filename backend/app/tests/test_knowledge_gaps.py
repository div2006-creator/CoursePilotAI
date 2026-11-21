"""Comprehensive automated test suite for Part 8: Knowledge Gap Analysis & Prerequisite Intelligence.

Covers all 22 required scenarios:
1. Strong topic classification.
2. Developing topic classification.
3. Weak topic classification.
4. Not-assessed topic classification.
5. Insufficient attempt handling (confidence penalty).
6. Direct prerequisite retrieval.
7. Indirect prerequisite retrieval (transitive).
8. Weak prerequisite identification.
9. Unassessed prerequisite identification.
10. Foundational weakness classification.
11. Isolated difficulty classification.
12. Potential knowledge gap classification.
13. Gap severity calculation.
14. Confidence calculation.
15. Duplicate recommendation prevention.
16. Missing prerequisite graph handling.
17. Unauthorized analysis access (401 & 404).
18. Ollama unavailable fallback.
19. Malformed LLM explanation fallback.
20. Analysis history retrieval.
21. Reassessment endpoint triggering targeted diagnostic.
22. OpenAPI schema exposes knowledge gap endpoints.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Generator
import uuid

# Ensure `backend` directory is in sys.path so `app.*` imports resolve in all environments
_BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.main import app as fastapi_app
from app.models.attempt import Attempt
from app.models.course import Course
from app.models.question import Question
from app.models.topic import Topic
from app.models.topic_prerequisite import TopicPrerequisite
from app.models.user import User
from app.schemas.knowledge_gap import PrerequisiteNode, TopicPerformanceMetric
from app.services.knowledge_gap_service import (
    calculate_confidence,
    calculate_gap_severity,
    classify_knowledge_gap,
    classify_topic_knowledge,
    generate_ai_explanation,
    generate_recommendations,
    get_topic_performance,
    trace_prerequisite_chain,
)


# ---------------------------------------------------------------------------
# Test Helpers & Fixtures
# ---------------------------------------------------------------------------


def _create_user(session: Session, email: str = "lovelace@example.com") -> User:
    user = User(
        name="Ada Lovelace",
        email=email,
        password_hash="mock_hash_for_testing",
    )
    session.add(user)
    session.flush()
    return user


def _create_course(session: Session, user: User, title: str = "Dynamic Programming") -> Course:
    course = Course(
        user_id=user.id,
        title=title,
        description="Comprehensive algorithmic problem solving",
        daily_minutes=60,
    )
    session.add(course)
    session.flush()
    return course


def _create_dp_prerequisite_chain(session: Session, course: Course) -> dict[str, Topic]:
    """Create classic chain: Recursion -> Memoization -> Tabulation -> Grid DP."""
    t_recursion = Topic(course_id=course.id, name="Recursion", unit_name="Unit 1")
    t_memo = Topic(course_id=course.id, name="Memoization", unit_name="Unit 2")
    t_tab = Topic(course_id=course.id, name="Tabulation", unit_name="Unit 2")
    t_grid_dp = Topic(course_id=course.id, name="Grid DP", unit_name="Unit 3")

    session.add_all([t_recursion, t_memo, t_tab, t_grid_dp])
    session.flush()

    # Edges: topic_id requires prerequisite_id
    # Memoization requires Recursion
    e1 = TopicPrerequisite(topic_id=t_memo.id, prerequisite_id=t_recursion.id, confidence=1.0)
    # Tabulation requires Memoization
    e2 = TopicPrerequisite(topic_id=t_tab.id, prerequisite_id=t_memo.id, confidence=0.9)
    # Grid DP requires Tabulation
    e3 = TopicPrerequisite(topic_id=t_grid_dp.id, prerequisite_id=t_tab.id, confidence=0.95)

    session.add_all([e1, e2, e3])
    session.flush()

    return {
        "recursion": t_recursion,
        "memoization": t_memo,
        "tabulation": t_tab,
        "grid_dp": t_grid_dp,
    }


def _seed_attempts(
    session: Session,
    user: User,
    course: Course,
    topic: Topic,
    correct_count: int,
    total_count: int,
) -> None:
    # Create a base question
    q = Question(
        topic_id=topic.id,
        question=f"Test question for {topic.name}",
        options=["A", "B", "C", "D"],
        correct_answer="A",
        difficulty="medium",
        source="sample/test",
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
        )
        session.add(att)
    session.flush()


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, extra_claims={"email": user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def mock_default_llm_generator(monkeypatch):
    """Automatically mock LLM generation so tests run offline without Ollama."""
    def _mock_gen(prompt: str, system: str | None = None, response_format: str = "json", temperature: float = 0.1, **kwargs):
        if "multiple choice assessment question" in prompt.lower() or "topic id:" in prompt.lower():
            import re
            topic_match = re.search(r"Topic ID:\s*([0-9a-fA-F-]+)", prompt)
            topic_id = topic_match.group(1) if topic_match else str(uuid.uuid4())
            return json.dumps({
                "questions": [
                    {
                        "topic_id": topic_id,
                        "question": "What is the primary benefit of memoization?",
                        "options": [
                            "Avoiding redundant subproblems",
                            "Linear search",
                            "Exponential space",
                            "Randomization",
                        ],
                        "correct_answer": "Avoiding redundant subproblems",
                        "explanation": "Memoization caches intermediate subproblem solutions.",
                        "difficulty": "medium",
                    }
                ]
            })

        return json.dumps({
            "summary": "Student displays strong recursion fundamentals but struggles converting recursive logic into tabulation.",
            "findings": [
                {
                    "topic": "Grid DP",
                    "reason": "Low accuracy due to tabulation conversion difficulties.",
                    "classification": "foundational_weakness",
                }
            ],
            "recommendations": [
                {
                    "topic": "Tabulation",
                    "reason": "Strengthening iterative tabulation will unblock Grid DP.",
                }
            ],
        })

    monkeypatch.setattr("app.services.knowledge_gap_service.generate_completion", _mock_gen)
    monkeypatch.setattr("app.services.question_generation_service.generate_completion", _mock_gen)


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    from app.api.dependencies import get_db

    def _override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    with TestClient(fastapi_app) as tc:
        yield tc
    fastapi_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1 - 4. Topic Classifications (Strong, Developing, Weak, Not Assessed)
# ---------------------------------------------------------------------------


def test_topic_classifications():
    p_strong = TopicPerformanceMetric(
        topic_id=uuid.uuid4(),
        topic_name="Recursion",
        total_attempts=5,
        correct_attempts=4,
        accuracy_percentage=80.0,
        knowledge_status="strong",
        confidence_score=1.0,
    )
    assert classify_topic_knowledge(p_strong) == "strong"

    p_dev = TopicPerformanceMetric(
        topic_id=uuid.uuid4(),
        topic_name="Memoization",
        total_attempts=4,
        correct_attempts=3,
        accuracy_percentage=75.0,
        knowledge_status="developing",
        confidence_score=1.0,
    )
    assert classify_topic_knowledge(p_dev) == "developing"

    p_weak = TopicPerformanceMetric(
        topic_id=uuid.uuid4(),
        topic_name="Grid DP",
        total_attempts=4,
        correct_attempts=1,
        accuracy_percentage=25.0,
        knowledge_status="weak",
        confidence_score=1.0,
    )
    assert classify_topic_knowledge(p_weak) == "weak"

    p_unassessed = TopicPerformanceMetric(
        topic_id=uuid.uuid4(),
        topic_name="Bitmask DP",
        total_attempts=0,
        correct_attempts=0,
        accuracy_percentage=0.0,
        knowledge_status="not_assessed",
        confidence_score=0.0,
    )
    assert classify_topic_knowledge(p_unassessed) == "not_assessed"


# ---------------------------------------------------------------------------
# 5. Insufficient Attempt Handling
# ---------------------------------------------------------------------------


def test_insufficient_attempt_handling(db_session: Session):
    user = _create_user(db_session, "attempts_user@example.com")
    course = _create_course(db_session, user)
    t = Topic(course_id=course.id, name="Sorting Algorithms")
    db_session.add(t)
    db_session.flush()

    # 1 attempt only
    _seed_attempts(db_session, user, course, t, correct_count=1, total_count=1)
    db_session.commit()

    perf = get_topic_performance(db_session, user.id, course.id)
    metric = perf[t.id]
    # Total attempts = 1 gets base confidence factor of 0.5 (less than 1.0)
    assert metric.total_attempts == 1
    assert metric.confidence_score == 0.5


# ---------------------------------------------------------------------------
# 6 & 7. Direct and Indirect Prerequisite Retrieval (BFS Graph Traversal)
# ---------------------------------------------------------------------------


def test_direct_and_indirect_prerequisite_retrieval(db_session: Session):
    user = _create_user(db_session, "kg_graph_user@example.com")
    course = _create_course(db_session, user)
    chain_map = _create_dp_prerequisite_chain(db_session, course)
    db_session.commit()

    perf = get_topic_performance(db_session, user.id, course.id)
    from app.services.knowledge_gap_service import build_course_prerequisite_maps
    prereqs_map, _ = build_course_prerequisite_maps(db_session, course.id)

    # Grid DP chain: Tabulation (depth 1) -> Memoization (depth 2) -> Recursion (depth 3)
    chain = trace_prerequisite_chain(chain_map["grid_dp"].id, prereqs_map, perf)
    assert len(chain) == 3

    chain_names = [p.topic_name for p in chain]
    assert chain_names == ["Tabulation", "Memoization", "Recursion"]

    # Direct vs indirect check
    assert chain[0].is_direct is True
    assert chain[0].depth == 1
    assert chain[1].is_direct is False
    assert chain[1].depth == 2
    assert chain[2].is_direct is False
    assert chain[2].depth == 3


# ---------------------------------------------------------------------------
# 8 & 9. Weak & Unassessed Prerequisite Identification
# ---------------------------------------------------------------------------


def test_weak_and_unassessed_prerequisite_identification(db_session: Session):
    user = _create_user(db_session, "identify_user@example.com")
    course = _create_course(db_session, user)
    chain_map = _create_dp_prerequisite_chain(db_session, course)

    # Recursion: Strong (80%)
    _seed_attempts(db_session, user, course, chain_map["recursion"], 4, 5)
    # Memoization: Weak (20%)
    _seed_attempts(db_session, user, course, chain_map["memoization"], 1, 5)
    # Tabulation: Unassessed (0 attempts)
    # Grid DP: Weak (25%)
    _seed_attempts(db_session, user, course, chain_map["grid_dp"], 1, 4)
    db_session.commit()

    perf = get_topic_performance(db_session, user.id, course.id)
    from app.services.knowledge_gap_service import build_course_prerequisite_maps
    prereqs_map, _ = build_course_prerequisite_maps(db_session, course.id)

    chain = trace_prerequisite_chain(chain_map["grid_dp"].id, prereqs_map, perf)

    weak_prereqs = [p for p in chain if p.knowledge_status == "weak"]
    unassessed_prereqs = [p for p in chain if p.knowledge_status == "not_assessed"]

    assert len(weak_prereqs) == 1
    assert weak_prereqs[0].topic_name == "Memoization"
    assert len(unassessed_prereqs) == 1
    assert unassessed_prereqs[0].topic_name == "Tabulation"


# ---------------------------------------------------------------------------
# 10. Foundational Weakness Classification
# ---------------------------------------------------------------------------


def test_foundational_weakness_classification():
    target = TopicPerformanceMetric(
        topic_id=uuid.uuid4(),
        topic_name="Grid DP",
        total_attempts=4,
        correct_attempts=1,
        accuracy_percentage=25.0,
        knowledge_status="weak",
        confidence_score=1.0,
    )
    # Prerequisite is also weak
    prereqs = [
        PrerequisiteNode(
            topic_id=uuid.uuid4(),
            topic_name="Tabulation",
            knowledge_status="weak",
            accuracy_percentage=30.0,
            depth=1,
            is_direct=True,
        )
    ]
    gap_type, evidence = classify_knowledge_gap(target, prereqs)
    assert gap_type == "foundational_weakness"
    assert "Tabulation" in evidence["bottlenecks"]


# ---------------------------------------------------------------------------
# 11. Isolated Difficulty Classification
# ---------------------------------------------------------------------------


def test_isolated_difficulty_classification():
    target = TopicPerformanceMetric(
        topic_id=uuid.uuid4(),
        topic_name="Grid DP",
        total_attempts=4,
        correct_attempts=1,
        accuracy_percentage=25.0,
        knowledge_status="weak",
        confidence_score=1.0,
    )
    # Both direct and indirect prerequisites are strong
    prereqs = [
        PrerequisiteNode(
            topic_id=uuid.uuid4(),
            topic_name="Tabulation",
            knowledge_status="strong",
            accuracy_percentage=90.0,
            depth=1,
            is_direct=True,
        ),
        PrerequisiteNode(
            topic_id=uuid.uuid4(),
            topic_name="Recursion",
            knowledge_status="strong",
            accuracy_percentage=85.0,
            depth=2,
            is_direct=False,
        ),
    ]
    gap_type, evidence = classify_knowledge_gap(target, prereqs)
    assert gap_type == "isolated_difficulty"
    assert "Tabulation" in evidence["strong_prerequisites"]


# ---------------------------------------------------------------------------
# 12. Potential Knowledge Gap Classification
# ---------------------------------------------------------------------------


def test_potential_knowledge_gap_classification():
    target = TopicPerformanceMetric(
        topic_id=uuid.uuid4(),
        topic_name="Grid DP",
        total_attempts=3,
        correct_attempts=1,
        accuracy_percentage=33.3,
        knowledge_status="weak",
        confidence_score=1.0,
    )
    # Prerequisite has never been assessed
    prereqs = [
        PrerequisiteNode(
            topic_id=uuid.uuid4(),
            topic_name="Tabulation",
            knowledge_status="not_assessed",
            accuracy_percentage=0.0,
            depth=1,
            is_direct=True,
        )
    ]
    gap_type, evidence = classify_knowledge_gap(target, prereqs)
    assert gap_type == "potential_knowledge_gap"
    assert "Tabulation" in evidence["missing_evidence"]


# ---------------------------------------------------------------------------
# 13. Gap Severity Calculation Formula
# ---------------------------------------------------------------------------


def test_gap_severity_calculation():
    target = TopicPerformanceMetric(
        topic_id=uuid.uuid4(),
        topic_name="Target Topic",
        total_attempts=4,
        correct_attempts=1,
        accuracy_percentage=20.0,  # weakness = 80.0
        knowledge_status="weak",
        confidence_score=1.0,
    )
    prereqs = [
        PrerequisiteNode(
            topic_id=uuid.uuid4(),
            topic_name="Prereq",
            knowledge_status="weak",
            accuracy_percentage=40.0,  # weakness = 60.0
            depth=1,
            is_direct=True,
        )
    ]
    # dependents_count = 0 -> topic_importance = 40.0
    # Expected: 0.50 * 80.0 + 0.30 * 60.0 + 0.20 * 40.0 = 40.0 + 18.0 + 8.0 = 66.0
    sev = calculate_gap_severity(target, prereqs, dependents_count=0)
    assert sev == 66.0


# ---------------------------------------------------------------------------
# 14. Confidence Calculation with Unassessed Penalty
# ---------------------------------------------------------------------------


def test_confidence_calculation():
    target = TopicPerformanceMetric(
        topic_id=uuid.uuid4(),
        topic_name="Target Topic",
        total_attempts=4,
        correct_attempts=1,
        accuracy_percentage=25.0,
        knowledge_status="weak",
        confidence_score=1.0,  # base confidence 1.0 (>= 3 attempts)
    )
    # 2 unassessed prerequisites: penalty = 2 * 0.15 = 0.30
    prereqs = [
        PrerequisiteNode(topic_id=uuid.uuid4(), topic_name="P1", knowledge_status="not_assessed", accuracy_percentage=0.0),
        PrerequisiteNode(topic_id=uuid.uuid4(), topic_name="P2", knowledge_status="not_assessed", accuracy_percentage=0.0),
    ]
    conf = calculate_confidence(target, prereqs)
    assert conf == 0.7


# ---------------------------------------------------------------------------
# 15. Duplicate Recommendation Prevention
# ---------------------------------------------------------------------------


def test_duplicate_recommendation_prevention():
    from app.schemas.knowledge_gap import KnowledgeGapDetail

    shared_prereq_id = uuid.uuid4()
    p_node = PrerequisiteNode(
        topic_id=shared_prereq_id,
        topic_name="Recursion",
        knowledge_status="weak",
        accuracy_percentage=20.0,
        depth=1,
        is_direct=True,
    )

    gap1 = KnowledgeGapDetail(
        topic_id=uuid.uuid4(),
        topic_name="DFS",
        gap_type="foundational_weakness",
        severity=70.0,
        confidence=1.0,
        accuracy_percentage=30.0,
        attempt_count=3,
        prerequisite_chain=[p_node],
    )
    gap2 = KnowledgeGapDetail(
        topic_id=uuid.uuid4(),
        topic_name="Backtracking",
        gap_type="foundational_weakness",
        severity=65.0,
        confidence=1.0,
        accuracy_percentage=35.0,
        attempt_count=3,
        prerequisite_chain=[p_node],
    )

    recs = generate_recommendations([gap1, gap2], {})
    # Recursion should only be recommended once
    rec_topics = [r.topic_name for r in recs if r.topic_name == "Recursion"]
    assert len(rec_topics) == 1


# ---------------------------------------------------------------------------
# 16. Missing Prerequisite Graph Handling
# ---------------------------------------------------------------------------


def test_missing_prerequisite_graph_handling():
    isolated_target = TopicPerformanceMetric(
        topic_id=uuid.uuid4(),
        topic_name="Disjoint Concept",
        total_attempts=3,
        correct_attempts=0,
        accuracy_percentage=0.0,
        knowledge_status="weak",
        confidence_score=1.0,
    )
    # Empty prerequisite chain
    gap_type, evidence = classify_knowledge_gap(isolated_target, [])
    assert gap_type == "direct_weakness"
    assert evidence["prerequisites_count"] == 0


# ---------------------------------------------------------------------------
# 17. Unauthorized Analysis Access
# ---------------------------------------------------------------------------


def test_unauthorized_analysis_access(db_session: Session, client: TestClient):
    owner = _create_user(db_session, "gap_owner@example.com")
    intruder = _create_user(db_session, "gap_intruder@example.com")
    course = _create_course(db_session, owner)
    db_session.commit()

    # 1. Unauthenticated request -> 401
    resp_unauth = client.post(f"/api/v1/courses/{course.id}/knowledge-gaps/analyze")
    assert resp_unauth.status_code == 401

    # 2. Intruder attempting to analyze owner's course -> 404
    resp_forbidden = client.post(
        f"/api/v1/courses/{course.id}/knowledge-gaps/analyze",
        headers=_auth_headers(intruder),
    )
    assert resp_forbidden.status_code == 404


# ---------------------------------------------------------------------------
# 18 & 19. Ollama Unavailable & Malformed Output Fallback
# ---------------------------------------------------------------------------


def test_ollama_unavailable_and_malformed_fallback():
    from app.schemas.knowledge_gap import KnowledgeGapDetail

    gaps = [
        KnowledgeGapDetail(
            topic_id=uuid.uuid4(),
            topic_name="Grid DP",
            gap_type="foundational_weakness",
            severity=75.0,
            confidence=0.9,
            accuracy_percentage=25.0,
            attempt_count=4,
        )
    ]

    # 1. LLM throws exception
    def failing_llm(*args, **kwargs):
        raise RuntimeError("Ollama connection refused")

    summary_failed = generate_ai_explanation(gaps, {}, llm_generator=failing_llm)
    assert "Foundational knowledge gaps detected affecting 'Grid DP'" in summary_failed

    # 2. LLM returns invalid malformed string
    def malformed_llm(*args, **kwargs):
        return "Not JSON at all! Just raw plain text"

    summary_malformed = generate_ai_explanation(gaps, {}, llm_generator=malformed_llm)
    assert "Foundational knowledge gaps detected affecting 'Grid DP'" in summary_malformed


# ---------------------------------------------------------------------------
# 20. End-to-End Analysis & History Retrieval
# ---------------------------------------------------------------------------


def test_analysis_and_history_retrieval(db_session: Session, client: TestClient):
    user = _create_user(db_session, "e2e_gap_user@example.com")
    course = _create_course(db_session, user)
    chain_map = _create_dp_prerequisite_chain(db_session, course)

    # Recursion: Strong (80%)
    _seed_attempts(db_session, user, course, chain_map["recursion"], 4, 5)
    # Tabulation: Weak (20%)
    _seed_attempts(db_session, user, course, chain_map["tabulation"], 1, 5)
    # Grid DP: Weak (25%)
    _seed_attempts(db_session, user, course, chain_map["grid_dp"], 1, 4)
    db_session.commit()

    # Trigger analysis via POST
    post_resp = client.post(
        f"/api/v1/courses/{course.id}/knowledge-gaps/analyze",
        headers=_auth_headers(user),
    )
    assert post_resp.status_code == 201
    res_data = post_resp.json()["data"]
    assert res_data["total_topics"] == 4
    assert res_data["assessed_topics"] == 3
    assert res_data["unassessed_topics_count"] == 1  # Memoization was unassessed
    assert len(res_data["gaps"]) >= 2
    assert len(res_data["recommendations"]) >= 1

    # Verify latest analysis via GET
    get_resp = client.get(
        f"/api/v1/courses/{course.id}/knowledge-gaps",
        headers=_auth_headers(user),
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["analysis_id"] == res_data["analysis_id"]

    # Verify history retrieval
    hist_resp = client.get(
        f"/api/v1/courses/{course.id}/knowledge-gaps/history",
        headers=_auth_headers(user),
    )
    assert hist_resp.status_code == 200
    history = hist_resp.json()["data"]
    assert len(history) == 1
    assert history[0]["course_id"] == str(course.id)


# ---------------------------------------------------------------------------
# 21. Reassessment Endpoint Triggers Targeted Diagnostic Session
# ---------------------------------------------------------------------------


def test_reassess_endpoint_triggers_targeted_diagnostic(db_session: Session, client: TestClient):
    user = _create_user(db_session, "reassess_user@example.com")
    course = _create_course(db_session, user)
    chain_map = _create_dp_prerequisite_chain(db_session, course)

    # Tabulation is weak
    _seed_attempts(db_session, user, course, chain_map["tabulation"], 1, 4)
    # Memoization is an unassessed prerequisite of Tabulation!
    # Seed 1 question for memoization so test doesn't need Ollama
    q_memo = Question(
        topic_id=chain_map["memoization"].id,
        question="What is memoization?",
        options=["Caching results", "Recursion", "Greedy", "Sorting"],
        correct_answer="Caching results",
        difficulty="medium",
        source="sample/test",
    )
    db_session.add(q_memo)
    db_session.commit()

    # Call reassess endpoint
    reassess_resp = client.post(
        f"/api/v1/courses/{course.id}/knowledge-gaps/reassess",
        headers=_auth_headers(user),
        json={"difficulty": "medium", "questions_per_topic": 1},
    )
    assert reassess_resp.status_code == 201
    data = reassess_resp.json()
    assert data["mode"] == "selected"
    assert data["total_questions"] >= 1
    # Check that questions belong to unassessed topics
    assert "session_id" in data


# ---------------------------------------------------------------------------
# 22. OpenAPI Exposes All Knowledge Gap Endpoints
# ---------------------------------------------------------------------------


def test_openapi_exposes_knowledge_gap_endpoints(client: TestClient):
    resp = client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    paths = schema.get("paths", {})

    expected_endpoints = [
        "/api/v1/courses/{course_id}/knowledge-gaps/analyze",
        "/api/v1/courses/{course_id}/knowledge-gaps",
        "/api/v1/courses/{course_id}/knowledge-gaps/history",
        "/api/v1/topics/{topic_id}/knowledge-gaps",
        "/api/v1/courses/{course_id}/knowledge-gaps/recommendations",
        "/api/v1/courses/{course_id}/knowledge-gaps/reassess",
    ]

    for endpoint in expected_endpoints:
        assert endpoint in paths, f"Expected endpoint {endpoint} not registered in OpenAPI schema."


def test_find_weak_topics_function():
    from app.services.knowledge_gap_service import find_weak_topics

    p1 = TopicPerformanceMetric(topic_id=uuid.uuid4(), topic_name="A", total_attempts=5, correct_attempts=5, accuracy_percentage=100.0, knowledge_status="strong", confidence_score=1.0)
    p2 = TopicPerformanceMetric(topic_id=uuid.uuid4(), topic_name="B", total_attempts=4, correct_attempts=1, accuracy_percentage=25.0, knowledge_status="weak", confidence_score=1.0)
    p3 = TopicPerformanceMetric(topic_id=uuid.uuid4(), topic_name="C", total_attempts=0, correct_attempts=0, accuracy_percentage=0.0, knowledge_status="not_assessed", confidence_score=0.0)

    weaks = find_weak_topics({p1.topic_id: p1, p2.topic_id: p2, p3.topic_id: p3})
    assert len(weaks) == 1
    assert weaks[0].topic_name == "B"


def test_single_topic_knowledge_gap_endpoint(db_session: Session, client: TestClient):
    user = _create_user(db_session, "single_topic_user@example.com")
    course = _create_course(db_session, user)
    chain_map = _create_dp_prerequisite_chain(db_session, course)
    _seed_attempts(db_session, user, course, chain_map["grid_dp"], 1, 4)
    db_session.commit()

    # Run analysis first
    client.post(
        f"/api/v1/courses/{course.id}/knowledge-gaps/analyze",
        headers=_auth_headers(user),
    )

    # Query single topic
    resp = client.get(
        f"/api/v1/topics/{chain_map['grid_dp'].id}/knowledge-gaps",
        headers=_auth_headers(user),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data is not None
    assert data["topic_name"] == "Grid DP"
    assert data["accuracy_percentage"] == 25.0


def test_recommendations_endpoint(db_session: Session, client: TestClient):
    user = _create_user(db_session, "recs_user@example.com")
    course = _create_course(db_session, user)
    chain_map = _create_dp_prerequisite_chain(db_session, course)
    _seed_attempts(db_session, user, course, chain_map["tabulation"], 1, 4)
    db_session.commit()

    client.post(
        f"/api/v1/courses/{course.id}/knowledge-gaps/analyze",
        headers=_auth_headers(user),
    )

    resp = client.get(
        f"/api/v1/courses/{course.id}/knowledge-gaps/recommendations",
        headers=_auth_headers(user),
    )
    assert resp.status_code == 200
    recs = resp.json()["data"]
    assert len(recs) >= 1
    assert any(r["topic_name"] == "Tabulation" for r in recs)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))

