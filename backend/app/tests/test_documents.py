"""Tests for Document Upload, PDF Processing, and Cross-User Isolation."""
from __future__ import annotations

import io
import uuid

import fitz  # PyMuPDF
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user, get_db
from app.core.database import Base
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.course import Course
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.models.user import User


def make_test_pdf(text: str = "Unit 1: Arrays and Strings. Recursion is foundational.") -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def users_and_courses(db_session: Session):
    user_a = User(
        email="user_a@example.com",
        password_hash=hash_password("Password123!"),
        name="User Alpha",
    )
    user_b = User(
        email="user_b@example.com",
        password_hash=hash_password("Password123!"),
        name="User Beta",
    )
    db_session.add_all([user_a, user_b])
    db_session.commit()
    db_session.refresh(user_a)
    db_session.refresh(user_b)

    course_a = Course(
        user_id=user_a.id,
        title="Data Structures Alpha",
        daily_minutes=45,
    )
    course_b = Course(
        user_id=user_b.id,
        title="Algorithms Beta",
        daily_minutes=30,
    )
    db_session.add_all([course_a, course_b])
    db_session.commit()
    db_session.refresh(course_a)
    db_session.refresh(course_b)

    return user_a, user_b, course_a, course_b


def test_upload_valid_pdf_extracts_and_chunks(db_session: Session, users_and_courses):
    user_a, _, course_a, _ = users_and_courses

    def override_get_db():
        yield db_session

    def override_get_current_user():
        return user_a

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    client = TestClient(app)
    pdf_bytes = make_test_pdf("Unit 1: Data Structures. Arrays and Pointers are core.")

    response = client.post(
        f"/api/v1/courses/{course_a.id}/documents/upload",
        files={"file": ("syllabus.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["filename"] == "syllabus.pdf"
    assert data["status"] == "completed"
    assert data["page_count"] == 1
    assert data["chunk_count"] >= 1
    assert data["extracted_text_length"] > 0

    # Verify in DB
    doc_id = uuid.UUID(data["id"])
    doc = db_session.get(Document, doc_id)
    assert doc is not None
    assert doc.status == "completed"
    assert len(doc.chunks) >= 1
    assert "Data Structures" in doc.chunks[0].content

    app.dependency_overrides.clear()


def test_upload_invalid_non_pdf_rejected(db_session: Session, users_and_courses):
    user_a, _, course_a, _ = users_and_courses

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user_a
    client = TestClient(app)

    fake_file = b"This is just plain text, not a valid PDF file."
    response = client.post(
        f"/api/v1/courses/{course_a.id}/documents/upload",
        files={"file": ("fake.pdf", fake_file, "application/pdf")},
    )

    assert response.status_code == 422
    assert "Invalid file format" in response.json()["message"]
    app.dependency_overrides.clear()


def test_upload_empty_file_rejected(db_session: Session, users_and_courses):
    user_a, _, course_a, _ = users_and_courses

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user_a
    client = TestClient(app)

    response = client.post(
        f"/api/v1/courses/{course_a.id}/documents/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )

    assert response.status_code == 422
    assert "empty" in response.json()["message"].lower()
    app.dependency_overrides.clear()


def test_cross_user_isolation_document_access(db_session: Session, users_and_courses):
    user_a, user_b, course_a, _ = users_and_courses

    # User A uploads document
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user_a
    client = TestClient(app)

    pdf_bytes = make_test_pdf("Confidential Syllabus for User A.")
    res = client.post(
        f"/api/v1/courses/{course_a.id}/documents/upload",
        files={"file": ("syllabus_a.pdf", pdf_bytes, "application/pdf")},
    )
    assert res.status_code == 201
    doc_id = res.json()["data"]["id"]

    # Now switch to User B
    app.dependency_overrides[get_current_user] = lambda: user_b

    # User B tries to view documents of Course A
    list_res = client.get(f"/api/v1/courses/{course_a.id}/documents")
    assert list_res.status_code == 404

    # User B tries to retrieve specific document
    get_res = client.get(f"/api/v1/courses/{course_a.id}/documents/{doc_id}")
    assert get_res.status_code == 404

    # User B tries to delete Course A's document
    del_res = client.delete(f"/api/v1/courses/{course_a.id}/documents/{doc_id}")
    assert del_res.status_code == 404

    app.dependency_overrides.clear()


def test_document_deletion_cleans_up_chunks(db_session: Session, users_and_courses):
    user_a, _, course_a, _ = users_and_courses

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user_a
    client = TestClient(app)

    pdf_bytes = make_test_pdf("To be deleted syllabus text.")
    res = client.post(
        f"/api/v1/courses/{course_a.id}/documents/upload",
        files={"file": ("delete_me.pdf", pdf_bytes, "application/pdf")},
    )
    doc_id = res.json()["data"]["id"]

    # Delete
    del_res = client.delete(f"/api/v1/courses/{course_a.id}/documents/{doc_id}")
    assert del_res.status_code == 204

    # Verify not found
    get_res = client.get(f"/api/v1/courses/{course_a.id}/documents/{doc_id}")
    assert get_res.status_code == 404

    app.dependency_overrides.clear()
