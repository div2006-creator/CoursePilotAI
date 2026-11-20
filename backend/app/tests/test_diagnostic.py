"""Comprehensive test suite for Part 7: Diagnostic Assessment Engine.

Covers:
1. Start full diagnostic assessment.
2. Start topic-specific diagnostic assessment.
3. Start without topics (empty course rejects).
4. Unauthorized diagnostic creation and access.
5. Question generation with valid LLM output (mocked).
6. Malformed LLM response handled gracefully.
7. Invalid topic IDs rejected.
8. Questions returned without correct answers or explanations (security verification).
9. Correct answer evaluation.
10. Incorrect answer evaluation.
11. Overall accuracy calculation.
12. Topic-wise accuracy calculation (strong, moderate, weak).
13. Submission with an unknown question ID rejected.
14. Submission to another user's diagnostic rejected.
15. Duplicate submission rejection.
16. Result retrieval.
17. Diagnostic history retrieval.
18. OpenAPI schema exposes diagnostic endpoints.
"""
from __future__ import annotations

import json
from typing import Generator
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.main import app as fastapi_app
from app.models.attempt import Attempt
from app.models.course import Course
from app.models.diagnostic_session import DiagnosticSession
from app.models.question import Question
from app.models.topic import Topic
from app.models.user import User
from app.schemas.diagnostic import DiagnosticStartRequest, DiagnosticSubmitRequest
from app.services.assessment_analytics_service import (
    calculate_difficulty_breakdown,
    calculate_diagnostic_score,
    calculate_topic_wise_accuracy,
    classify_accuracy_status,
)
from app.services.diagnostic_service import (
    start_diagnostic_session,
    submit_diagnostic,
)
from app.services.question_generation_service import (
    InvalidQuestionDataError,
    parse_and_validate_questions_json,
)


# ---------------------------------------------------------------------------
# Test Helpers & Fixtures
# ---------------------------------------------------------------------------


def _create_user(session: Session, email: str = "curie@example.com") -> User:
    user = User(
        name="Marie Curie",
        email=email,
        password_hash="mock_hash_for_testing",
    )
    session.add(user)
    session.flush()
    return user


def _create_course(session: Session, user: User, title: str = "Algorithms") -> Course:
    course = Course(
        user_id=user.id,
        title=title,
        description="Core algorithmic problem solving",
        daily_minutes=45,
    )
    session.add(course)
    session.flush()
    return course


def _create_topics(session: Session, course: Course) -> list[Topic]:
    t1 = Topic(
        course_id=course.id,
        name="Arrays and Strings",
        description="Linear contiguous memory structures",
        difficulty="beginner",
        unit_name="Unit 1: Linear Structures",
    )
    t2 = Topic(
        course_id=course.id,
        name="Binary Search Trees",
        description="Hierarchical non-linear search structures",
        difficulty="intermediate",
        unit_name="Unit 2: Trees and Graphs",
    )
    session.add_all([t1, t2])
    session.flush()
    return [t1, t2]


def _create_question(
    session: Session,
    topic: Topic,
    question_text: str = "What is the time complexity of array lookup by index?",
    options: list[str] = None,
    correct_answer: str = "O(1)",
    difficulty: str = "easy",
) -> Question:
    if options is None:
        options = ["O(1)", "O(n)", "O(log n)", "O(n^2)"]
    q = Question(
        topic_id=topic.id,
        question=question_text,
        options=options,
        correct_answer=correct_answer,
        explanation="Array indexing is a direct memory address calculation.",
        difficulty=difficulty,
        source="sample/test",
    )
    session.add(q)
    session.flush()
    return q


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, extra_claims={"email": user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def mock_default_llm_generator(monkeypatch):
    """Automatically mock LLM generation so tests run offline without Ollama."""
    def _mock_gen(prompt: str, system: str = None, response_format: str = "json", temperature: float = 0.1, **kwargs):
        import re
        topic_match = re.search(r"Topic ID:\s*([0-9a-fA-F-]+)", prompt)
        topic_id = topic_match.group(1) if topic_match else str(uuid.uuid4())
        return json.dumps({
            "questions": [
                {
                    "topic_id": topic_id,
                    "question": "What is the time complexity of binary search?",
                    "options": ["O(log n)", "O(n)", "O(1)", "O(n^2)"],
                    "correct_answer": "O(log n)",
                    "explanation": "Search space is halved each step.",
                    "difficulty": "medium",
                }
            ]
        })

    monkeypatch.setattr("app.services.question_generation_service.generate_completion", _mock_gen)


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
# 1. Start Full Diagnostic Assessment
# ---------------------------------------------------------------------------


def test_start_full_diagnostic_success(db_session: Session, client: TestClient):
    user = _create_user(db_session, "user1@example.com")
    course = _create_course(db_session, user)
    topics = _create_topics(db_session, course)

    # Seed existing questions
    q1 = _create_question(db_session, topics[0], "Q1 Array?", difficulty="easy")
    q2 = _create_question(db_session, topics[1], "Q2 BST?", difficulty="medium")
    db_session.commit()

    resp = client.post(
        f"/api/v1/courses/{course.id}/diagnostic/start",
        headers=_auth_headers(user),
        json={
            "mode": "full",
            "difficulty": "mixed",
            "questions_per_topic": 1,
        },
    )

    assert resp.status_code == 201
    data = resp.json()
    assert "session_id" in data
    assert data["course_id"] == str(course.id)
    assert data["mode"] == "full"
    assert data["status"] == "in_progress"
    assert data["total_questions"] >= 2
    assert len(data["questions"]) >= 2

    # Verify SECURITY rule: answers and explanations MUST NOT be leaked
    for q in data["questions"]:
        assert "correct_answer" not in q
        assert "explanation" not in q
        assert "options" in q
        assert len(q["options"]) == 4


# ---------------------------------------------------------------------------
# 2. Start Topic-Specific Diagnostic Assessment
# ---------------------------------------------------------------------------


def test_start_topic_specific_diagnostic(db_session: Session, client: TestClient):
    user = _create_user(db_session, "user2@example.com")
    course = _create_course(db_session, user)
    topics = _create_topics(db_session, course)

    _create_question(db_session, topics[0], "Array Question 1")
    _create_question(db_session, topics[1], "BST Question 1")
    db_session.commit()

    # Request only topic 0
    resp = client.post(
        f"/api/v1/courses/{course.id}/diagnostic/start",
        headers=_auth_headers(user),
        json={
            "mode": "selected",
            "topic_ids": [str(topics[0].id)],
            "questions_per_topic": 1,
        },
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["mode"] == "selected"
    assert data["total_questions"] == 1
    assert data["questions"][0]["topic_id"] == str(topics[0].id)


# ---------------------------------------------------------------------------
# 3. Start Without Topics (Empty Course Rejection)
# ---------------------------------------------------------------------------


def test_start_diagnostic_empty_course_rejected(db_session: Session, client: TestClient):
    user = _create_user(db_session, "user3@example.com")
    empty_course = _create_course(db_session, user, "Empty Course")
    db_session.commit()

    resp = client.post(
        f"/api/v1/courses/{empty_course.id}/diagnostic/start",
        headers=_auth_headers(user),
        json={"mode": "full"},
    )

    assert resp.status_code == 400
    assert "no topics available" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 4. Unauthorized Diagnostic Creation & Access
# ---------------------------------------------------------------------------


def test_start_diagnostic_unauthorized(db_session: Session, client: TestClient):
    owner = _create_user(db_session, "owner@example.com")
    intruder = _create_user(db_session, "intruder@example.com")
    course = _create_course(db_session, owner)
    _create_topics(db_session, course)
    db_session.commit()

    # 1. Unauthenticated request
    unauth_resp = client.post(
        f"/api/v1/courses/{course.id}/diagnostic/start",
        json={"mode": "full"},
    )
    assert unauth_resp.status_code == 401

    # 2. Authenticated intruder accessing owner's course
    forbidden_resp = client.post(
        f"/api/v1/courses/{course.id}/diagnostic/start",
        headers=_auth_headers(intruder),
        json={"mode": "full"},
    )
    assert forbidden_resp.status_code == 404


# ---------------------------------------------------------------------------
# 5. Question Generation with Valid LLM Output
# ---------------------------------------------------------------------------


def test_question_generation_with_valid_llm_output(db_session: Session):
    user = _create_user(db_session, "llm_user@example.com")
    course = _create_course(db_session, user)
    topics = _create_topics(db_session, course)
    target_topic = topics[0]

    mock_llm_payload = json.dumps({
        "questions": [
            {
                "topic_id": str(target_topic.id),
                "question": "Which data structure uses LIFO ordering?",
                "options": ["Queue", "Stack", "Array", "Linked List"],
                "correct_answer": "Stack",
                "explanation": "A stack operates on Last-In, First-Out principle.",
                "difficulty": "easy",
            }
        ]
    })

    def mock_generator(*args, **kwargs):
        return mock_llm_payload

    session, questions = start_diagnostic_session(
        db=db_session,
        user_id=user.id,
        course_id=course.id,
        payload=DiagnosticStartRequest(
            mode="selected",
            topic_ids=[target_topic.id],
            questions_per_topic=1,
        ),
        llm_generator=mock_generator,
    )

    assert session is not None
    assert len(questions) == 1
    assert questions[0].question == "Which data structure uses LIFO ordering?"
    assert questions[0].correct_answer == "Stack"
    assert questions[0].difficulty == "easy"
    assert questions[0].source == "ai_generated"


# ---------------------------------------------------------------------------
# 6. Malformed LLM Response Handled Gracefully
# ---------------------------------------------------------------------------


def test_question_generation_malformed_llm_response(db_session: Session):
    user = _create_user(db_session, "malformed_llm@example.com")
    course = _create_course(db_session, user)
    topics = _create_topics(db_session, course)

    # 1. Invalid JSON string
    with pytest.raises(InvalidQuestionDataError):
        parse_and_validate_questions_json(
            raw_text="This is not JSON at all",
            allowed_topic_ids={topics[0].id},
        )

    # 2. Options not containing 4 items
    bad_options_json = json.dumps({
        "questions": [
            {
                "topic_id": str(topics[0].id),
                "question": "What is 2+2?",
                "options": ["3", "4"],
                "correct_answer": "4",
                "difficulty": "easy",
            }
        ]
    })
    with pytest.raises(InvalidQuestionDataError):
        parse_and_validate_questions_json(
            raw_text=bad_options_json,
            allowed_topic_ids={topics[0].id},
        )


# ---------------------------------------------------------------------------
# 7. Invalid Topic IDs Rejected
# ---------------------------------------------------------------------------


def test_invalid_topic_ids_rejected(db_session: Session, client: TestClient):
    user = _create_user(db_session, "invalid_topic_user@example.com")
    course = _create_course(db_session, user)
    _create_topics(db_session, course)
    db_session.commit()

    random_id = str(uuid.uuid4())
    resp = client.post(
        f"/api/v1/courses/{course.id}/diagnostic/start",
        headers=_auth_headers(user),
        json={
            "mode": "selected",
            "topic_ids": [random_id],
        },
    )

    assert resp.status_code == 400
    assert "one or more selected topics do not belong" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 8. Questions Endpoint Hides Correct Answers and Explanations
# ---------------------------------------------------------------------------


def test_questions_endpoint_hides_answers_and_explanations(db_session: Session, client: TestClient):
    user = _create_user(db_session, "security_user@example.com")
    course = _create_course(db_session, user)
    topics = _create_topics(db_session, course)
    _create_question(db_session, topics[0], "Confidential Question")
    db_session.commit()

    start_resp = client.post(
        f"/api/v1/courses/{course.id}/diagnostic/start",
        headers=_auth_headers(user),
        json={
            "mode": "selected",
            "topic_ids": [str(topics[0].id)],
            "questions_per_topic": 1,
        },
    )
    assert start_resp.status_code == 201
    session_id = start_resp.json()["session_id"]

    # Fetch questions via GET
    get_resp = client.get(
        f"/api/v1/diagnostic/{session_id}/questions",
        headers=_auth_headers(user),
    )
    assert get_resp.status_code == 200
    q_data = get_resp.json()

    question_texts = [item["question"] for item in q_data["questions"]]
    assert "Confidential Question" in question_texts

    for item in q_data["questions"]:
        assert "correct_answer" not in item
        assert "explanation" not in item


# ---------------------------------------------------------------------------
# 9 & 10. Correct and Incorrect Answer Evaluation
# ---------------------------------------------------------------------------


def test_correct_and_incorrect_answer_evaluation(db_session: Session, client: TestClient):
    user = _create_user(db_session, "eval_user@example.com")
    course = _create_course(db_session, user)
    topics = _create_topics(db_session, course)

    q1 = _create_question(
        db_session, topics[0], "Q1", options=["A", "B", "C", "D"], correct_answer="A"
    )
    q2 = _create_question(
        db_session, topics[1], "Q2", options=["W", "X", "Y", "Z"], correct_answer="Z"
    )
    db_session.commit()

    start_resp = client.post(
        f"/api/v1/courses/{course.id}/diagnostic/start",
        headers=_auth_headers(user),
        json={
            "mode": "selected",
            "topic_ids": [str(topics[0].id), str(topics[1].id)],
            "questions_per_topic": 1,
        },
    )
    session_id = start_resp.json()["session_id"]

    # Submit Q1 correct ("A"), Q2 incorrect ("W")
    submit_resp = client.post(
        f"/api/v1/diagnostic/{session_id}/submit",
        headers=_auth_headers(user),
        json={
            "answers": [
                {"question_id": str(q1.id), "selected_answer": "A", "time_taken": 15},
                {"question_id": str(q2.id), "selected_answer": "W", "time_taken": 25},
            ]
        },
    )

    assert submit_resp.status_code == 200
    res = submit_resp.json()["data"]
    assert res["status"] == "completed"
    assert res["total_questions"] == 2
    assert res["correct_answers"] == 1
    assert res["incorrect_answers"] == 1
    assert res["score"] == 50.0

    # Verify attempts in DB
    attempts = list(
        db_session.execute(
            select(Attempt).where(Attempt.diagnostic_session_id == uuid.UUID(session_id))
        ).scalars().all()
    )
    assert len(attempts) == 2
    att_map = {a.question_id: a for a in attempts}
    assert att_map[q1.id].is_correct is True
    assert att_map[q2.id].is_correct is False


# ---------------------------------------------------------------------------
# 11. Score Calculation Helper
# ---------------------------------------------------------------------------


def test_overall_score_calculation():
    assert calculate_diagnostic_score(0, 0) == 0.0
    assert calculate_diagnostic_score(0, 5) == 0.0
    assert calculate_diagnostic_score(3, 4) == 75.0
    assert calculate_diagnostic_score(1, 3) == 33.3
    assert calculate_diagnostic_score(5, 5) == 100.0


# ---------------------------------------------------------------------------
# 12. Topic-Wise Accuracy & Mastery Classification
# ---------------------------------------------------------------------------


def test_topic_wise_accuracy_calculation(db_session: Session):
    user = _create_user(db_session, "analytics_user@example.com")
    course = _create_course(db_session, user)
    topics = _create_topics(db_session, course)
    t1, t2 = topics[0], topics[1]

    q1 = _create_question(db_session, t1, "T1 Q1", correct_answer="A")
    q2 = _create_question(db_session, t1, "T1 Q2", correct_answer="B")
    q3 = _create_question(db_session, t2, "T2 Q1", correct_answer="C")

    # t1: 2 correct out of 2 (100% -> strong)
    att1 = Attempt(user_id=user.id, course_id=course.id, topic_id=t1.id, question_id=q1.id, selected_answer="A", is_correct=True)
    att2 = Attempt(user_id=user.id, course_id=course.id, topic_id=t1.id, question_id=q2.id, selected_answer="B", is_correct=True)
    # t2: 0 correct out of 1 (0% -> weak)
    att3 = Attempt(user_id=user.id, course_id=course.id, topic_id=t2.id, question_id=q3.id, selected_answer="Wrong", is_correct=False)

    topics_map = {t1.id: t1, t2.id: t2}
    topic_acc = calculate_topic_wise_accuracy([att1, att2, att3], topics_map)

    acc_dict = {item.topic_id: item for item in topic_acc}
    assert acc_dict[t1.id].accuracy_percentage == 100.0
    assert acc_dict[t1.id].status == "strong"
    assert acc_dict[t2.id].accuracy_percentage == 0.0
    assert acc_dict[t2.id].status == "weak"

    assert classify_accuracy_status(80.0, 5) == "strong"
    assert classify_accuracy_status(60.0, 5) == "moderate"
    assert classify_accuracy_status(40.0, 5) == "weak"
    assert classify_accuracy_status(0.0, 0) == "not_assessed"


# ---------------------------------------------------------------------------
# 13. Submission with Unknown Question ID Rejected
# ---------------------------------------------------------------------------


def test_submission_with_unknown_question_rejected(db_session: Session, client: TestClient):
    user = _create_user(db_session, "unknown_q_user@example.com")
    course = _create_course(db_session, user)
    topics = _create_topics(db_session, course)
    _create_question(db_session, topics[0])
    db_session.commit()

    start_resp = client.post(
        f"/api/v1/courses/{course.id}/diagnostic/start",
        headers=_auth_headers(user),
        json={
            "mode": "selected",
            "topic_ids": [str(topics[0].id)],
            "questions_per_topic": 1,
        },
    )
    session_id = start_resp.json()["session_id"]

    fake_q_id = str(uuid.uuid4())
    submit_resp = client.post(
        f"/api/v1/diagnostic/{session_id}/submit",
        headers=_auth_headers(user),
        json={
            "answers": [
                {"question_id": fake_q_id, "selected_answer": "A"}
            ]
        },
    )

    assert submit_resp.status_code == 400
    assert "does not belong" in submit_resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 14. Submission to Another User's Diagnostic Rejected
# ---------------------------------------------------------------------------


def test_submission_to_another_users_diagnostic_rejected(db_session: Session, client: TestClient):
    alice = _create_user(db_session, "alice@example.com")
    bob = _create_user(db_session, "bob@example.com")
    course = _create_course(db_session, alice)
    topics = _create_topics(db_session, course)
    q = _create_question(db_session, topics[0])
    db_session.commit()

    # Alice starts a session
    start_resp = client.post(
        f"/api/v1/courses/{course.id}/diagnostic/start",
        headers=_auth_headers(alice),
        json={
            "mode": "selected",
            "topic_ids": [str(topics[0].id)],
            "questions_per_topic": 1,
        },
    )
    session_id = start_resp.json()["session_id"]

    # Bob tries to submit to Alice's session
    submit_resp = client.post(
        f"/api/v1/diagnostic/{session_id}/submit",
        headers=_auth_headers(bob),
        json={
            "answers": [
                {"question_id": str(q.id), "selected_answer": "A"}
            ]
        },
    )

    assert submit_resp.status_code == 403


# ---------------------------------------------------------------------------
# 15. Duplicate Submission Rejection
# ---------------------------------------------------------------------------


def test_duplicate_submission_rejected(db_session: Session, client: TestClient):
    user = _create_user(db_session, "dup_sub_user@example.com")
    course = _create_course(db_session, user)
    topics = _create_topics(db_session, course)
    q = _create_question(db_session, topics[0], options=["A", "B", "C", "D"], correct_answer="A")
    db_session.commit()

    start_resp = client.post(
        f"/api/v1/courses/{course.id}/diagnostic/start",
        headers=_auth_headers(user),
        json={
            "mode": "selected",
            "topic_ids": [str(topics[0].id)],
            "questions_per_topic": 1,
        },
    )
    session_id = start_resp.json()["session_id"]

    payload = {"answers": [{"question_id": str(q.id), "selected_answer": "A"}]}

    # First submit succeeds
    first_resp = client.post(
        f"/api/v1/diagnostic/{session_id}/submit",
        headers=_auth_headers(user),
        json=payload,
    )
    assert first_resp.status_code == 200

    # Second submit fails with 400
    second_resp = client.post(
        f"/api/v1/diagnostic/{session_id}/submit",
        headers=_auth_headers(user),
        json=payload,
    )
    assert second_resp.status_code == 400
    assert "already been completed" in second_resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 16. Result Retrieval
# ---------------------------------------------------------------------------


def test_result_retrieval(db_session: Session, client: TestClient):
    user = _create_user(db_session, "result_user@example.com")
    course = _create_course(db_session, user)
    topics = _create_topics(db_session, course)
    q = _create_question(db_session, topics[0], options=["A", "B", "C", "D"], correct_answer="A")
    db_session.commit()

    start_resp = client.post(
        f"/api/v1/courses/{course.id}/diagnostic/start",
        headers=_auth_headers(user),
        json={
            "mode": "selected",
            "topic_ids": [str(topics[0].id)],
            "questions_per_topic": 1,
        },
    )
    session_id = start_resp.json()["session_id"]

    # Submit
    client.post(
        f"/api/v1/diagnostic/{session_id}/submit",
        headers=_auth_headers(user),
        json={"answers": [{"question_id": str(q.id), "selected_answer": "A"}]},
    )

    # Get Result
    res_resp = client.get(
        f"/api/v1/diagnostic/{session_id}/result",
        headers=_auth_headers(user),
    )
    assert res_resp.status_code == 200
    data = res_resp.json()["data"]
    assert data["session_id"] == session_id
    assert data["score"] == 100.0
    assert len(data["questions_review"]) >= 1
    assert data["questions_review"][0]["is_correct"] is True
    assert data["questions_review"][0]["correct_answer"] == "A"
    assert "Arrays and Strings" in data["strongest_topics"]


# ---------------------------------------------------------------------------
# 17. Diagnostic History Retrieval
# ---------------------------------------------------------------------------


def test_diagnostic_history_retrieval(db_session: Session, client: TestClient):
    user = _create_user(db_session, "history_user@example.com")
    course = _create_course(db_session, user)
    topics = _create_topics(db_session, course)
    q = _create_question(db_session, topics[0])
    db_session.commit()

    # Create two sessions
    for _ in range(2):
        client.post(
            f"/api/v1/courses/{course.id}/diagnostic/start",
            headers=_auth_headers(user),
            json={
            "mode": "selected",
            "topic_ids": [str(topics[0].id)],
            "questions_per_topic": 1,
        },
        )

    hist_resp = client.get(
        f"/api/v1/courses/{course.id}/diagnostic/history",
        headers=_auth_headers(user),
    )
    assert hist_resp.status_code == 200
    history = hist_resp.json()["data"]
    assert len(history) == 2
    assert history[0]["course_id"] == str(course.id)


# ---------------------------------------------------------------------------
# 18. OpenAPI Exposes All Diagnostic Endpoints
# ---------------------------------------------------------------------------


def test_openapi_exposes_diagnostic_endpoints(client: TestClient):
    resp = client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    paths = schema.get("paths", {})

    expected_endpoints = [
        "/api/v1/courses/{course_id}/diagnostic/start",
        "/api/v1/diagnostic/{diagnostic_id}/questions",
        "/api/v1/diagnostic/{diagnostic_id}/submit",
        "/api/v1/diagnostic/{diagnostic_id}/result",
        "/api/v1/courses/{course_id}/diagnostic/history",
    ]

    for endpoint in expected_endpoints:
        assert endpoint in paths, f"Expected endpoint {endpoint} not registered in OpenAPI schema."
