from __future__ import annotations

from datetime import date, timedelta
import uuid

from fastapi.testclient import TestClient

AUTH_PREFIX = "/api/v1/auth"
COURSES_PREFIX = "/api/v1/courses"


def _auth_headers(client: TestClient, *, name: str, email: str, password: str = "StrongPass123!") -> dict[str, str]:
    reg = client.post(
        f"{AUTH_PREFIX}/register",
        json={"name": name, "email": email, "password": password},
    )
    assert reg.status_code == 201

    login = client.post(
        f"{AUTH_PREFIX}/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_course(
    client: TestClient,
    headers: dict[str, str],
    *,
    title: str = "Data Structures and Algorithms",
    description: str | None = "Trees, graphs, dynamic programming, and complexity.",
    exam_date: str | None = None,
    daily_minutes: int = 90,
):
    payload: dict = {
        "title": title,
        "description": description,
        "daily_minutes": daily_minutes,
    }
    if exam_date is not None:
        payload["exam_date"] = exam_date
    return client.post(COURSES_PREFIX, json=payload, headers=headers)


# ---------------------------------------------------------------------------
# 1. Create Course (Authenticated vs Unauthenticated)
# ---------------------------------------------------------------------------


def test_authenticated_user_can_create_course(client: TestClient) -> None:
    headers = _auth_headers(client, name="Alice", email="alice.course@example.com")
    future_date = (date.today() + timedelta(days=14)).isoformat()

    res = _create_course(
        client,
        headers,
        title="Data Structures and Algorithms",
        description="Core CS201 curriculum",
        exam_date=future_date,
        daily_minutes=90,
    )
    assert res.status_code == 201

    body = res.json()
    assert body["success"] is True
    assert body["message"] == "Course created successfully"

    data = body["data"]
    assert uuid.UUID(data["id"])
    assert data["title"] == "Data Structures and Algorithms"
    assert data["description"] == "Core CS201 curriculum"
    assert data["exam_date"] == future_date
    assert data["daily_minutes"] == 90
    assert data["days_remaining"] == 14
    assert data["is_exam_passed"] is False
    assert data["exam_status"] == "upcoming"
    assert "created_at" in data


def test_unauthenticated_user_cannot_create_or_access_courses(client: TestClient) -> None:
    create_res = client.post(
        COURSES_PREFIX,
        json={"title": "Unauthorized Course", "daily_minutes": 60},
    )
    assert create_res.status_code == 401

    list_res = client.get(COURSES_PREFIX)
    assert list_res.status_code == 401


def test_past_exam_date_is_allowed_and_flagged_gracefully(client: TestClient) -> None:
    headers = _auth_headers(client, name="Past Exam", email="past.exam@example.com")
    past_date = (date.today() - timedelta(days=5)).isoformat()

    res = _create_course(
        client,
        headers,
        title="Computer Networks",
        exam_date=past_date,
        daily_minutes=60,
    )
    assert res.status_code == 201

    data = res.json()["data"]
    assert data["exam_date"] == past_date
    assert data["is_exam_passed"] is True
    assert data["days_remaining"] == -5
    assert data["exam_status"] == "passed"


# ---------------------------------------------------------------------------
# 2. Retrieve & Isolate User Courses
# ---------------------------------------------------------------------------


def test_user_retrieves_only_own_courses_and_supports_search(client: TestClient) -> None:
    alice_headers = _auth_headers(client, name="Alice", email="alice.list@example.com")
    bob_headers = _auth_headers(client, name="Bob", email="bob.list@example.com")

    _create_course(client, alice_headers, title="Machine Learning", daily_minutes=120)
    _create_course(client, alice_headers, title="Database Management Systems", daily_minutes=60)
    _create_course(client, bob_headers, title="Bob Secret Course", daily_minutes=45)

    res = client.get(COURSES_PREFIX, headers=alice_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["total"] == 2
    titles = {c["title"] for c in body["data"]["courses"]}
    assert titles == {"Machine Learning", "Database Management Systems"}

    # Search filter
    search_res = client.get(f"{COURSES_PREFIX}?search=machine", headers=alice_headers)
    assert search_res.status_code == 200
    assert search_res.json()["data"]["total"] == 1
    assert search_res.json()["data"]["courses"][0]["title"] == "Machine Learning"


def test_user_cannot_view_another_users_course(client: TestClient) -> None:
    alice_headers = _auth_headers(client, name="Alice", email="alice.view@example.com")
    bob_headers = _auth_headers(client, name="Bob", email="bob.view@example.com")

    created = _create_course(client, alice_headers, title="Software Engineering")
    course_id = created.json()["data"]["id"]

    # Owner can view
    owner_res = client.get(f"{COURSES_PREFIX}/{course_id}", headers=alice_headers)
    assert owner_res.status_code == 200
    assert owner_res.json()["data"]["id"] == course_id

    # Another user gets 404 (never reveals existence)
    other_res = client.get(f"{COURSES_PREFIX}/{course_id}", headers=bob_headers)
    assert other_res.status_code == 404
    assert other_res.json()["success"] is False


# ---------------------------------------------------------------------------
# 3. Update Course (Owner vs Non-Owner)
# ---------------------------------------------------------------------------


def test_user_can_update_own_course(client: TestClient) -> None:
    headers = _auth_headers(client, name="Alice", email="alice.update@example.com")
    initial_exam = (date.today() + timedelta(days=20)).isoformat()
    created = _create_course(
        client,
        headers,
        title="Original DSA",
        description="Old description",
        exam_date=initial_exam,
        daily_minutes=60,
    )
    course_id = created.json()["data"]["id"]

    new_exam = (date.today() + timedelta(days=5)).isoformat()
    update_res = client.patch(
        f"{COURSES_PREFIX}/{course_id}",
        json={
            "title": "Advanced DSA",
            "daily_minutes": 150,
            "exam_date": new_exam,
        },
        headers=headers,
    )
    assert update_res.status_code == 200
    data = update_res.json()["data"]
    assert data["title"] == "Advanced DSA"
    assert data["description"] == "Old description"  # Untouched field preserved
    assert data["daily_minutes"] == 150
    assert data["exam_date"] == new_exam
    assert data["exam_status"] == "urgent"

    # Explicitly clearing optional description and exam_date
    clear_res = client.patch(
        f"{COURSES_PREFIX}/{course_id}",
        json={"description": None, "exam_date": None},
        headers=headers,
    )
    assert clear_res.status_code == 200
    cleared = clear_res.json()["data"]
    assert cleared["description"] is None
    assert cleared["exam_date"] is None
    assert cleared["exam_status"] == "no_exam_date"


def test_user_cannot_update_another_users_course(client: TestClient) -> None:
    alice_headers = _auth_headers(client, name="Alice", email="alice.patch@example.com")
    bob_headers = _auth_headers(client, name="Bob", email="bob.patch@example.com")

    created = _create_course(client, alice_headers, title="Operating Systems")
    course_id = created.json()["data"]["id"]

    res = client.patch(
        f"{COURSES_PREFIX}/{course_id}",
        json={"title": "Hacked Title"},
        headers=bob_headers,
    )
    assert res.status_code == 404

    # Verify original course remains unchanged
    check = client.get(f"{COURSES_PREFIX}/{course_id}", headers=alice_headers)
    assert check.json()["data"]["title"] == "Operating Systems"


# ---------------------------------------------------------------------------
# 4. Delete Course (Owner vs Non-Owner)
# ---------------------------------------------------------------------------


def test_user_can_delete_own_course(client: TestClient) -> None:
    headers = _auth_headers(client, name="Alice", email="alice.delete@example.com")
    created = _create_course(client, headers, title="Discrete Mathematics")
    course_id = created.json()["data"]["id"]

    del_res = client.delete(f"{COURSES_PREFIX}/{course_id}", headers=headers)
    assert del_res.status_code == 204
    assert del_res.content == b""

    get_res = client.get(f"{COURSES_PREFIX}/{course_id}", headers=headers)
    assert get_res.status_code == 404


def test_user_cannot_delete_another_users_course(client: TestClient) -> None:
    alice_headers = _auth_headers(client, name="Alice", email="alice.delother@example.com")
    bob_headers = _auth_headers(client, name="Bob", email="bob.delother@example.com")

    created = _create_course(client, alice_headers, title="Compiler Design")
    course_id = created.json()["data"]["id"]

    del_res = client.delete(f"{COURSES_PREFIX}/{course_id}", headers=bob_headers)
    assert del_res.status_code == 404

    # Confirm course still exists for Alice
    still_there = client.get(f"{COURSES_PREFIX}/{course_id}", headers=alice_headers)
    assert still_there.status_code == 200


# ---------------------------------------------------------------------------
# 5. Validation & Missing Resource Tests
# ---------------------------------------------------------------------------


def test_invalid_daily_study_time_and_title_rejected(client: TestClient) -> None:
    headers = _auth_headers(client, name="Validator", email="validator@example.com")

    too_low = _create_course(client, headers, title="Valid Course", daily_minutes=10)
    assert too_low.status_code == 422
    assert too_low.json()["success"] is False

    too_high = _create_course(client, headers, title="Valid Course", daily_minutes=800)
    assert too_high.status_code == 422
    assert too_high.json()["success"] is False

    short_title = _create_course(client, headers, title="A", daily_minutes=60)
    assert short_title.status_code == 422

    long_title = _create_course(client, headers, title="X" * 101, daily_minutes=60)
    assert long_title.status_code == 422

    bad_date = client.post(
        COURSES_PREFIX,
        json={"title": "Bad Date", "exam_date": "2026-99-99", "daily_minutes": 60},
        headers=headers,
    )
    assert bad_date.status_code == 422


def test_missing_course_returns_404(client: TestClient) -> None:
    headers = _auth_headers(client, name="Missing", email="missing@example.com")
    missing_id = uuid.uuid4()

    assert client.get(f"{COURSES_PREFIX}/{missing_id}", headers=headers).status_code == 404
    assert (
        client.patch(
            f"{COURSES_PREFIX}/{missing_id}",
            json={"title": "Nope"},
            headers=headers,
        ).status_code
        == 404
    )
    assert client.delete(f"{COURSES_PREFIX}/{missing_id}", headers=headers).status_code == 404


def test_openapi_exposes_all_course_endpoints(client: TestClient) -> None:
    schema = client.get("/api/v1/openapi.json").json()
    paths = schema["paths"]
    assert "/api/v1/courses" in paths
    assert "post" in paths["/api/v1/courses"]
    assert "get" in paths["/api/v1/courses"]
    assert "/api/v1/courses/{course_id}" in paths
    assert "get" in paths["/api/v1/courses/{course_id}"]
    assert "patch" in paths["/api/v1/courses/{course_id}"]
    assert "delete" in paths["/api/v1/courses/{course_id}"]

