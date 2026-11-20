"""Comprehensive test suite for Part 6: AI Topic Extraction and Knowledge Graph.

Covers all 14 required scenarios:
1. Extract topics from a sample syllabus.
2. No completed documents available.
3. Ollama server unavailable.
4. Malformed AI JSON.
5. Duplicate topics deduplication.
6. Missing prerequisite references.
7. Self-prerequisite rejection.
8. Circular prerequisite detection.
9. Valid prerequisite graph generation.
10. Correct graph edge direction (Prerequisite -> Dependent).
11. Unauthorized topic access.
12. Unauthorized topic editing.
13. Duplicate extraction idempotency.
14. Topic deletion and relationship cleanup.
"""
from __future__ import annotations

import json
from typing import Generator
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.llm import OllamaConnectionError
from app.core.security import create_access_token
from app.main import app as fastapi_app
from app.models.course import Course
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.topic import Topic
from app.models.topic_prerequisite import TopicPrerequisite
from app.models.user import User
from app.services.knowledge_graph_service import (
    build_topic_graph,
    get_course_topic_graph,
)
from app.services.topic_extraction_service import (
    NoCompletedDocumentsError,
    TopicExtractionError,
    extract_topics_from_course,
)
from app.services.topic_validation_service import (
    detect_prerequisite_cycles,
    validate_extracted_topics,
    validate_prerequisites,
)
from app.tests.fixtures.sample_syllabus import (
    SAMPLE_CIRCULAR_PREREQ_DICT,
    SAMPLE_CIRCULAR_PREREQ_JSON,
    SAMPLE_DSA_EXTRACTION_DICT,
    SAMPLE_DSA_LLM_OUTPUT_JSON,
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


def _create_course(session: Session, user: User, title: str = "DSA Algorithms") -> Course:
    course = Course(
        user_id=user.id,
        title=title,
        description="Core computer science data structures syllabus",
        daily_minutes=60,
    )
    session.add(course)
    session.flush()
    return course


def _create_completed_document_with_chunks(
    session: Session,
    course: Course,
    filename: str = "syllabus.pdf",
) -> Document:
    doc = Document(
        course_id=course.id,
        filename=filename,
        file_path=f"/uploads/{filename}",
        status="completed",
        file_size=10240,
        page_count=4,
    )
    session.add(doc)
    session.flush()

    chunks = [
        DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            content="Unit 1: Linear Data Structures. Arrays and Strings.",
            page_number=1,
        ),
        DocumentChunk(
            document_id=doc.id,
            chunk_index=1,
            content="Unit 2: Recursion and Backtracking state space search.",
            page_number=2,
        ),
        DocumentChunk(
            document_id=doc.id,
            chunk_index=2,
            content="Unit 3: Dynamic Programming, Memoization and Tabulation.",
            page_number=3,
        ),
        DocumentChunk(
            document_id=doc.id,
            chunk_index=3,
            content="Unit 4: Trees and Graphs. Traversals and Shortest Paths.",
            page_number=4,
        ),
    ]
    session.add_all(chunks)
    session.flush()
    return doc


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, extra_claims={"email": user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient that overrides get_db dependency with test database session."""
    from app.api.dependencies import get_db

    def _override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    with TestClient(fastapi_app) as tc:
        yield tc
    fastapi_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. Extract Topics from a Sample Syllabus
# ---------------------------------------------------------------------------


def test_extract_topics_from_sample_syllabus(db_session: Session, client: TestClient):
    user = _create_user(db_session, email="student1@example.com")
    course = _create_course(db_session, user, "CS201: DSA")
    _create_completed_document_with_chunks(db_session, course)

    # Mock LLM to return standard sample output
    def mock_llm(*args, **kwargs):
        return SAMPLE_DSA_LLM_OUTPUT_JSON

    res = extract_topics_from_course(db_session, course.id, user.id, llm_generator=mock_llm)
    assert res.success is True
    assert res.data.units_extracted >= 4
    assert res.data.topics_created >= 6
    assert res.data.prerequisites_created >= 4

    # Verify topics in database
    topics = db_session.scalars(
        select(Topic).where(Topic.course_id == course.id)
    ).all()
    topic_names = {t.name for t in topics}
    assert "Arrays" in topic_names
    assert "Recursion" in topic_names
    assert "Dynamic Programming" in topic_names

    # Check root vs subtopics
    dp_topic = next(t for t in topics if t.name == "Dynamic Programming")
    assert dp_topic.parent_id is None
    assert dp_topic.unit_name == "Unit 3: Dynamic Programming"
    assert len(dp_topic.subtopics) >= 1
    sub_names = {s.name for s in dp_topic.subtopics}
    assert "Memoization" in sub_names or "Tabulation" in sub_names


# ---------------------------------------------------------------------------
# 2. No Completed Documents Available
# ---------------------------------------------------------------------------


def test_extraction_fails_when_no_completed_documents(db_session: Session):
    user = _create_user(db_session, email="no_docs@example.com")
    course = _create_course(db_session, user, "Empty Course")

    with pytest.raises(NoCompletedDocumentsError) as exc_info:
        extract_topics_from_course(db_session, course.id, user.id)

    assert "No completed documents found" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 3. Ollama Server Unavailable
# ---------------------------------------------------------------------------


def test_extraction_handles_ollama_unavailable(db_session: Session, client: TestClient):
    user = _create_user(db_session, email="ollama_down@example.com")
    course = _create_course(db_session, user, "Offline Course")
    _create_completed_document_with_chunks(db_session, course)

    def mock_broken_llm(*args, **kwargs):
        raise OllamaConnectionError("Could not connect to Ollama server at http://localhost:11434")

    headers = _auth_headers(user)
    # Patch in topic extraction endpoint
    from unittest.mock import patch

    with patch("app.api.routes.topics.extract_topics_from_course") as mock_extract:
        mock_extract.side_effect = TopicExtractionError("Could not connect to Ollama server at http://localhost:11434")
        resp = client.post(
            f"/api/v1/courses/{course.id}/extract-topics",
            headers=headers,
        )
        assert resp.status_code == 503
        data = resp.json()
        assert data["success"] is False
        assert "connect to Ollama" in data["detail"]


# ---------------------------------------------------------------------------
# 4. Malformed AI JSON
# ---------------------------------------------------------------------------


def test_extraction_handles_malformed_ai_json(db_session: Session):
    user = _create_user(db_session, email="malformed@example.com")
    course = _create_course(db_session, user, "Malformed Course")
    _create_completed_document_with_chunks(db_session, course)

    def mock_bad_json(*args, **kwargs):
        return "I am an AI, and here are your topics: [Invalid JSON without close"

    with pytest.raises(TopicExtractionError) as exc_info:
        extract_topics_from_course(db_session, course.id, user.id, llm_generator=mock_bad_json)

    assert "validation failed" in str(exc_info.value) or "valid JSON" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 5. Duplicate Topics Deduplication
# ---------------------------------------------------------------------------


def test_duplicate_topics_are_deduplicated():
    raw_data = {
        "units": [
            {
                "unit_name": "Unit 1",
                "topics": [
                    {"name": "Arrays", "description": "Intro to arrays", "difficulty": "easy", "source_pages": [1]},
                    {"name": "Arrays", "description": "Contiguous memory", "difficulty": "easy", "source_pages": [2]},
                    {"name": "  arrays  ", "description": "Duplicated with spaces", "difficulty": "easy"},
                ],
            }
        ],
        "prerequisites": [],
    }
    result = validate_extracted_topics(raw_data)
    assert len(result.topics) == 1
    assert result.topics[0].name == "Arrays"
    assert result.topics[0].source_pages == [1, 2]


# ---------------------------------------------------------------------------
# 6. Missing Prerequisite References
# ---------------------------------------------------------------------------


def test_missing_prerequisite_references_are_discarded():
    raw_prereqs = [
        {"topic": "Quantum Computing", "prerequisite": "Arrays", "confidence": 0.9},
        {"topic": "Recursion", "prerequisite": "NonExistentTopic", "confidence": 0.8},
        {"topic": "Dynamic Programming", "prerequisite": "Recursion", "confidence": 0.95},
    ]
    known = {"Arrays", "Recursion", "Dynamic Programming"}
    validated = validate_prerequisites(raw_prereqs, known)
    # Only Recursion -> Dynamic Programming should survive because Quantum Computing & NonExistentTopic don't exist
    assert len(validated) == 1
    assert validated[0].topic_name == "Dynamic Programming"
    assert validated[0].prerequisite_name == "Recursion"


# ---------------------------------------------------------------------------
# 7. Self-Prerequisite Rejection
# ---------------------------------------------------------------------------


def test_self_prerequisite_is_rejected():
    raw_prereqs = [
        {"topic": "Recursion", "prerequisite": "Recursion", "confidence": 1.0},
        {"topic": "Arrays", "prerequisite": "Arrays", "confidence": 0.5},
    ]
    known = {"Recursion", "Arrays"}
    validated = validate_prerequisites(raw_prereqs, known)
    assert len(validated) == 0


# ---------------------------------------------------------------------------
# 8. Circular Prerequisite Detection
# ---------------------------------------------------------------------------


def test_circular_prerequisite_detection():
    # A -> B -> C -> A
    edges = [("A", "B"), ("B", "C"), ("C", "A")]
    assert detect_prerequisite_cycles(edges) is True

    # A -> B -> C (DAG)
    dag_edges = [("A", "B"), ("B", "C")]
    assert detect_prerequisite_cycles(dag_edges) is False


def test_circular_prerequisites_dropped_during_validation():
    result = validate_extracted_topics(SAMPLE_CIRCULAR_PREREQ_DICT)
    # The third edge completing the cycle must have been dropped
    assert len(result.prerequisites) == 2
    # Graph remains a DAG
    edge_pairs = [(p.prerequisite_name, p.topic_name) for p in result.prerequisites]
    assert detect_prerequisite_cycles(edge_pairs) is False


# ---------------------------------------------------------------------------
# 9. Valid Prerequisite Graph Generation
# ---------------------------------------------------------------------------


def test_valid_prerequisite_graph_generation(db_session: Session):
    user = _create_user(db_session, email="graph_user@example.com")
    course = _create_course(db_session, user, "Graph Theory Course")

    t_rec = Topic(course_id=course.id, name="Recursion", difficulty="medium", unit_name="Unit 1")
    t_dp = Topic(course_id=course.id, name="Dynamic Programming", difficulty="hard", unit_name="Unit 2")
    db_session.add_all([t_rec, t_dp])
    db_session.flush()

    link = TopicPrerequisite(
        topic_id=t_dp.id,
        prerequisite_id=t_rec.id,
        confidence=0.95,
        reason="Recursion teaches overlapping subproblem structure.",
    )
    db_session.add(link)
    db_session.flush()

    graph_res = get_course_topic_graph(db_session, course.id, user.id)
    assert graph_res.success is True
    assert graph_res.data.total_nodes == 2
    assert graph_res.data.total_edges == 1
    assert graph_res.data.is_dag is True


# ---------------------------------------------------------------------------
# 10. Correct Graph Edge Direction (Prerequisite -> Dependent Topic)
# ---------------------------------------------------------------------------


def test_graph_edge_direction_is_prerequisite_to_dependent(db_session: Session):
    user = _create_user(db_session, email="direction_check@example.com")
    course = _create_course(db_session, user)

    rec = Topic(course_id=course.id, name="Recursion", difficulty="medium")
    dp = Topic(course_id=course.id, name="Dynamic Programming", difficulty="hard")
    db_session.add_all([rec, dp])
    db_session.flush()

    link = TopicPrerequisite(topic_id=dp.id, prerequisite_id=rec.id, confidence=0.95)
    db_session.add(link)
    db_session.flush()

    graph = build_topic_graph([rec, dp], [link])
    assert len(graph.edges) == 1
    edge = graph.edges[0]
    # Source MUST be prerequisite (Recursion), Target MUST be dependent topic (DP)
    assert edge.source == str(rec.id)
    assert edge.target == str(dp.id)


# ---------------------------------------------------------------------------
# 11. Unauthorized Topic Access
# ---------------------------------------------------------------------------


def test_unauthorized_topic_access(db_session: Session, client: TestClient):
    alice = _create_user(db_session, email="alice_topics@example.com")
    bob = _create_user(db_session, email="bob_topics@example.com")

    alice_course = _create_course(db_session, alice, "Alice's Course")
    topic = Topic(course_id=alice_course.id, name="Secrets", difficulty="hard")
    db_session.add(topic)
    db_session.flush()

    bob_headers = _auth_headers(bob)

    # Bob tries to access Alice's course topics
    res = client.get(f"/api/v1/courses/{alice_course.id}/topics", headers=bob_headers)
    assert res.status_code == 404

    # Bob tries to access Alice's course topic graph
    res = client.get(f"/api/v1/courses/{alice_course.id}/topic-graph", headers=bob_headers)
    assert res.status_code == 404

    # Bob tries to access Alice's individual topic
    res = client.get(f"/api/v1/topics/{topic.id}", headers=bob_headers)
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# 12. Unauthorized Topic Editing
# ---------------------------------------------------------------------------


def test_unauthorized_topic_editing(db_session: Session, client: TestClient):
    alice = _create_user(db_session, email="alice_edit@example.com")
    bob = _create_user(db_session, email="bob_edit@example.com")

    course = _create_course(db_session, alice)
    topic = Topic(course_id=course.id, name="Algorithms", difficulty="medium")
    db_session.add(topic)
    db_session.flush()

    bob_headers = _auth_headers(bob)

    # Bob tries to PATCH Alice's topic
    res = client.patch(
        f"/api/v1/topics/{topic.id}",
        headers=bob_headers,
        json={"name": "Hacked Topic"},
    )
    assert res.status_code == 404

    # Bob tries to DELETE Alice's topic
    res = client.delete(f"/api/v1/topics/{topic.id}", headers=bob_headers)
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# 13. Duplicate Extraction Idempotency
# ---------------------------------------------------------------------------


def test_duplicate_extraction_idempotency(db_session: Session):
    user = _create_user(db_session, email="idempotent@example.com")
    course = _create_course(db_session, user, "Idempotent Course")
    _create_completed_document_with_chunks(db_session, course)

    def mock_llm(*args, **kwargs):
        return SAMPLE_DSA_LLM_OUTPUT_JSON

    # Run extraction first time
    res1 = extract_topics_from_course(db_session, course.id, user.id, llm_generator=mock_llm)
    assert res1.success is True
    first_topics_count = res1.data.topics_created

    # Run extraction a second time on the same course
    res2 = extract_topics_from_course(db_session, course.id, user.id, llm_generator=mock_llm)
    assert res2.success is True
    # Second run should update in-place, creating 0 new duplicates
    assert res2.data.topics_created == 0

    # Total root topics count in database should remain the same
    total_db_topics = db_session.scalars(
        select(Topic).where(Topic.course_id == course.id, Topic.parent_id.is_(None))
    ).all()
    assert len(total_db_topics) == first_topics_count


# ---------------------------------------------------------------------------
# 14. Topic Deletion and Relationship Cleanup
# ---------------------------------------------------------------------------


def test_topic_deletion_and_relationship_cleanup(db_session: Session, client: TestClient):
    user = _create_user(db_session, email="cleanup@example.com")
    course = _create_course(db_session, user)

    t1 = Topic(course_id=course.id, name="Prerequisite A", difficulty="easy")
    t2 = Topic(course_id=course.id, name="Target Topic B", difficulty="medium")
    t3 = Topic(course_id=course.id, name="Dependent C", difficulty="hard")
    db_session.add_all([t1, t2, t3])
    db_session.flush()

    # t1 -> t2 -> t3
    link1 = TopicPrerequisite(topic_id=t2.id, prerequisite_id=t1.id, confidence=0.9)
    link2 = TopicPrerequisite(topic_id=t3.id, prerequisite_id=t2.id, confidence=0.85)
    db_session.add_all([link1, link2])
    db_session.flush()

    headers = _auth_headers(user)

    # Delete t2 through API
    res = client.delete(f"/api/v1/topics/{t2.id}", headers=headers)
    assert res.status_code == 204

    # Verify t2 is gone
    assert db_session.scalar(select(Topic).where(Topic.id == t2.id)) is None

    # Verify links involving t2 were removed
    remaining_links = db_session.scalars(
        select(TopicPrerequisite).where(
            (TopicPrerequisite.topic_id == t2.id) | (TopicPrerequisite.prerequisite_id == t2.id)
        )
    ).all()
    assert len(remaining_links) == 0

    # Other topics remain intact
    assert db_session.scalar(select(Topic).where(Topic.id == t1.id)) is not None
    assert db_session.scalar(select(Topic).where(Topic.id == t3.id)) is not None


# ---------------------------------------------------------------------------
# 15. OpenAPI Exposes All Topic Endpoints
# ---------------------------------------------------------------------------


def test_openapi_exposes_topic_endpoints(client: TestClient):
    resp = client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]

    assert "/api/v1/courses/{course_id}/extract-topics" in paths
    assert "/api/v1/courses/{course_id}/topics" in paths
    assert "/api/v1/courses/{course_id}/topic-graph" in paths
    assert "/api/v1/topics/{topic_id}" in paths
