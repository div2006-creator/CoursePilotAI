from __future__ import annotations

from datetime import timedelta
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.services.auth_service import get_user_by_email

AUTH_PREFIX = "/api/v1/auth"


def _register_sample_user(
    client: TestClient,
    *,
    name: str = "Grace Hopper",
    email: str = "Grace.Hopper@Example.COM",
    password: str = "StrongPass123!",
):
    return client.post(
        f"{AUTH_PREFIX}/register",
        json={"name": name, "email": email, "password": password},
    )


def _login_user(client: TestClient, *, email: str, password: str):
    return client.post(
        f"{AUTH_PREFIX}/login",
        json={"email": email, "password": password},
    )


# ---------------------------------------------------------------------------
# 1. Registration Tests
# ---------------------------------------------------------------------------


def test_register_success(client: TestClient, db_session: Session) -> None:
    response = _register_sample_user(client)
    assert response.status_code == 201

    body = response.json()
    assert body["success"] is True
    assert body["message"] == "User registered successfully"

    data = body["data"]
    assert uuid.UUID(data["id"])
    assert data["name"] == "Grace Hopper"
    assert data["email"] == "grace.hopper@example.com"  # Normalized lowercase
    assert "created_at" in data
    assert "password" not in data
    assert "password_hash" not in data

    # Verify plain-text password is never stored in DB
    stored = get_user_by_email(db_session, "grace.hopper@example.com")
    assert stored is not None
    assert stored.password_hash != "StrongPass123!"
    assert stored.password_hash.startswith("$2b$")


def test_register_duplicate_email_rejected(client: TestClient) -> None:
    first = _register_sample_user(client, email="dup@example.com")
    assert first.status_code == 201

    # Attempt duplicate with different casing
    second = _register_sample_user(client, name="Other User", email="DUP@Example.com")
    assert second.status_code == 409

    body = second.json()
    assert body["success"] is False
    assert "already exists" in body["message"].lower()


def test_register_validation_errors(client: TestClient) -> None:
    # Password shorter than 8 characters
    short_pw = _register_sample_user(client, email="short@example.com", password="123")
    assert short_pw.status_code == 422
    assert short_pw.json()["success"] is False

    # Invalid email format
    bad_email = _register_sample_user(client, email="not-an-email", password="StrongPass123!")
    assert bad_email.status_code == 422
    assert bad_email.json()["success"] is False

    # Too-short name
    short_name = _register_sample_user(client, name="A", email="a@example.com")
    assert short_name.status_code == 422
    assert short_name.json()["success"] is False


# ---------------------------------------------------------------------------
# 2. Login Tests
# ---------------------------------------------------------------------------


def test_login_success(client: TestClient) -> None:
    _register_sample_user(client, email="login@example.com", password="CorrectPassword1!")

    response = _login_user(client, email="LOGIN@example.com", password="CorrectPassword1!")
    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Login successful"
    assert body["data"]["token_type"] == "bearer"
    assert isinstance(body["data"]["access_token"], str)
    assert len(body["data"]["access_token"]) > 20


def test_login_incorrect_password_and_unknown_email_share_generic_error(
    client: TestClient,
) -> None:
    _register_sample_user(client, email="known@example.com", password="RightPassword123")

    wrong_pw = _login_user(client, email="known@example.com", password="WrongPassword999")
    unknown_email = _login_user(client, email="nobody@example.com", password="RightPassword123")

    assert wrong_pw.status_code == 401
    assert unknown_email.status_code == 401

    wrong_body = wrong_pw.json()
    unknown_body = unknown_email.json()
    assert wrong_body["success"] is False
    assert unknown_body["success"] is False
    assert wrong_body["message"] == unknown_body["message"] == "Invalid email or password"


# ---------------------------------------------------------------------------
# 3. Protected /auth/me Endpoint Tests
# ---------------------------------------------------------------------------


def test_auth_me_with_valid_token(client: TestClient) -> None:
    reg = _register_sample_user(
        client,
        name="Alan Turing",
        email="alan@example.com",
        password="EnigmaPassword1!",
    )
    user_id = reg.json()["data"]["id"]

    login_res = _login_user(client, email="alan@example.com", password="EnigmaPassword1!")
    token = login_res.json()["data"]["access_token"]

    me_res = client.get(
        f"{AUTH_PREFIX}/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200

    body = me_res.json()
    assert body["success"] is True
    data = body["data"]
    assert data["id"] == user_id
    assert data["name"] == "Alan Turing"
    assert data["email"] == "alan@example.com"
    assert "created_at" in data
    assert "password" not in data
    assert "password_hash" not in data


def test_auth_me_without_token_returns_401(client: TestClient) -> None:
    response = client.get(f"{AUTH_PREFIX}/me")
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"
    assert response.json()["success"] is False


def test_auth_me_with_invalid_token_returns_401(client: TestClient) -> None:
    malformed = client.get(
        f"{AUTH_PREFIX}/me",
        headers={"Authorization": "Bearer not.a.valid.jwt.token"},
    )
    assert malformed.status_code == 401
    assert malformed.json()["success"] is False

    # Validly signed token referencing a nonexistent user UUID
    ghost_token = create_access_token(subject=uuid.uuid4())
    ghost = client.get(
        f"{AUTH_PREFIX}/me",
        headers={"Authorization": f"Bearer {ghost_token}"},
    )
    assert ghost.status_code == 401
    assert ghost.json()["success"] is False


def test_auth_me_with_expired_token_returns_401(client: TestClient) -> None:
    reg = _register_sample_user(
        client,
        email="expired@example.com",
        password="ExpiredPassword1!",
    )
    user_id = reg.json()["data"]["id"]

    expired_token = create_access_token(
        subject=user_id,
        expires_delta=timedelta(seconds=-10),
    )

    response = client.get(
        f"{AUTH_PREFIX}/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert "expired" in body["message"].lower()


# ---------------------------------------------------------------------------
# 4. Swagger / OpenAPI Integration Check
# ---------------------------------------------------------------------------


def test_openapi_exposes_auth_endpoints_and_bearer_scheme(client: TestClient) -> None:
    docs_res = client.get("/docs")
    assert docs_res.status_code == 200

    schema_res = client.get("/api/v1/openapi.json")
    assert schema_res.status_code == 200
    schema = schema_res.json()

    paths = schema["paths"]
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/me" in paths
    assert "/api/v1/health" in paths
    assert "BearerAuth" in schema["components"]["securitySchemes"]

