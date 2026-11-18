from __future__ import annotations

from datetime import date, datetime, timezone
import io
from pathlib import Path
import uuid

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import pytest
from sqlalchemy import Engine, create_engine, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import Base, DatabaseConnectionError, check_database_connection
from app.models import (
    AgentRun,
    Attempt,
    CircularPrerequisiteError,
    Course,
    Document,
    DocumentChunk,
    PlanItem,
    Question,
    StudyPlan,
    Topic,
    TopicMastery,
    TopicPrerequisite,
    User,
)
from app.tests.conftest import build_alembic_config

EXPECTED_TABLES = {
    "users",
    "courses",
    "documents",
    "document_chunks",
    "topics",
    "topic_prerequisites",
    "questions",
    "attempts",
    "topic_mastery",
    "study_plans",
    "plan_items",
    "agent_runs",
}


def _create_user(session: Session, email: str = "student@example.com") -> User:
    user = User(
        name="Ada Lovelace",
        email=email,
        password_hash="hashed_secret_placeholder",
    )
    session.add(user)
    session.flush()
    return user


def _create_course(session: Session, user: User, title: str = "CS201: DSA") -> Course:
    course = Course(
        user_id=user.id,
        title=title,
        description="Data Structures and Algorithms",
        exam_date=date(2026, 12, 20),
        daily_minutes=90,
    )
    session.add(course)
    session.flush()
    return course


def _create_topic(
    session: Session,
    course: Course,
    name: str,
    difficulty: str = "beginner",
    parent: Topic | None = None,
) -> Topic:
    topic = Topic(
        course_id=course.id,
        name=name,
        description=f"Concepts for {name}",
        difficulty=difficulty,
        parent_id=parent.id if parent else None,
    )
    session.add(topic)
    session.flush()
    return topic


# ---------------------------------------------------------------------------
# 1. Database Connectivity & Error Handling
# ---------------------------------------------------------------------------


def test_database_connection_check_succeeds(test_engine: Engine) -> None:
    is_connected, error = check_database_connection(test_engine)
    assert is_connected is True
    assert error is None


def test_database_connection_check_handles_invalid_url() -> None:
    bad_engine = create_engine(
        "postgresql+psycopg://invalid:invalid@127.0.0.1:1/nonexistent_db",
        connect_args={"connect_timeout": 1},
    )
    try:
        is_connected, error = check_database_connection(bad_engine)
        assert is_connected is False
        assert error is not None
        assert "Database connection failed" in error

        with pytest.raises(DatabaseConnectionError):
            check_database_connection(bad_engine, raise_on_error=True)
    finally:
        bad_engine.dispose()


# ---------------------------------------------------------------------------
# 2. Migrations (Upgrade, Downgrade, and PostgreSQL pgvector DDL)
# ---------------------------------------------------------------------------


def test_alembic_migrations_create_and_drop_all_tables(tmp_path: Path) -> None:
    isolated_db = tmp_path / "migration_roundtrip.sqlite3"
    url = f"sqlite:///{isolated_db.as_posix()}"
    cfg = build_alembic_config(url)
    engine = create_engine(url)
    try:
        command.upgrade(cfg, "head")
        created_tables = set(inspect(engine).get_table_names())
        assert EXPECTED_TABLES.issubset(created_tables)
        assert "alembic_version" in created_tables

        command.downgrade(cfg, "base")
        remaining_tables = set(inspect(engine).get_table_names())
        assert EXPECTED_TABLES.isdisjoint(remaining_tables)

        command.upgrade(cfg, "head")
        recreated_tables = set(inspect(engine).get_table_names())
        assert EXPECTED_TABLES.issubset(recreated_tables)
    finally:
        engine.dispose()


def test_alembic_postgresql_ddl_enables_pgvector_before_vector_column() -> None:
    sql_buffer = io.StringIO()
    cfg = build_alembic_config("postgresql+psycopg://postgres:postgres@localhost:5432/coursepilot")
    cfg.output_buffer = sql_buffer

    command.upgrade(cfg, "head", sql=True)
    ddl = sql_buffer.getvalue()

    ext_pos = ddl.find("CREATE EXTENSION IF NOT EXISTS vector")
    chunks_pos = ddl.find("CREATE TABLE document_chunks")
    assert ext_pos != -1, "Migration DDL must enable the pgvector extension"
    assert chunks_pos != -1, "Migration DDL must create document_chunks table"
    assert ext_pos < chunks_pos, "pgvector extension must be created before document_chunks"
    assert "VECTOR(384)" in ddl
    assert "JSONB" in ddl
    assert "UNIQUE (user_id, topic_id)" in ddl
    assert "CHECK (topic_id <> prerequisite_id)" in ddl


# ---------------------------------------------------------------------------
# 3. UUID Primary Keys, Timestamps & Full Relationships
# ---------------------------------------------------------------------------


def test_uuid_primary_keys_and_utc_timestamps(db_session: Session) -> None:
    user = _create_user(db_session, email="uuid.check@example.com")
    course = _create_course(db_session, user)

    assert isinstance(user.id, uuid.UUID)
    assert isinstance(course.id, uuid.UUID)
    assert user.id != course.id
    assert isinstance(user.created_at, datetime)
    assert user.created_at.tzinfo is not None or user.created_at <= datetime.now(timezone.utc).replace(tzinfo=None)


def test_full_relational_model_graph(db_session: Session) -> None:
    user = _create_user(db_session, email="graph.user@example.com")
    course = _create_course(db_session, user)

    doc = Document(
        course_id=course.id,
        filename="dsa_syllabus.pdf",
        file_path="/uploads/dsa_syllabus.pdf",
        status="processed",
    )
    db_session.add(doc)
    db_session.flush()

    embedding_vec = [0.01 * (i % 10) for i in range(384)]
    chunk = DocumentChunk(
        document_id=doc.id,
        content="Binary search runs in O(log n) worst-case time.",
        page_number=2,
        embedding=embedding_vec,
    )
    db_session.add(chunk)

    parent_topic = _create_topic(db_session, course, "Trees", difficulty="intermediate")
    child_topic = _create_topic(
        db_session,
        course,
        "Binary Search Trees",
        difficulty="intermediate",
        parent=parent_topic,
    )

    question = Question(
        topic_id=child_topic.id,
        question="Which traversal of a BST visits keys in sorted order?",
        options=["Preorder", "Inorder", "Postorder", "Level-order"],
        correct_answer="Inorder",
        explanation="Left -> Root -> Right visits BST keys in non-decreasing order.",
        difficulty="easy",
        source="seed",
    )
    db_session.add(question)
    db_session.flush()

    attempt = Attempt(
        user_id=user.id,
        course_id=course.id,
        topic_id=child_topic.id,
        question_id=question.id,
        selected_answer="Inorder",
        is_correct=True,
        time_taken=18,
    )
    mastery = TopicMastery(
        user_id=user.id,
        topic_id=child_topic.id,
        mastery_score=0.85,
        confidence_score=0.75,
    )
    plan = StudyPlan(
        user_id=user.id,
        course_id=course.id,
        version=1,
        status="active",
    )
    db_session.add_all([attempt, mastery, plan])
    db_session.flush()

    plan_item = PlanItem(
        plan_id=plan.id,
        topic_id=child_topic.id,
        scheduled_date=date(2026, 11, 20),
        duration_minutes=45,
        priority=1,
        status="pending",
    )
    agent_run = AgentRun(
        user_id=user.id,
        task_type="study_plan_generation",
        status="completed",
        input_data={"course_id": str(course.id)},
        output_data={"items_created": 1},
    )
    db_session.add_all([plan_item, agent_run])
    db_session.flush()

    # Verify bidirectional ORM relationships
    db_session.refresh(user)
    db_session.refresh(course)
    db_session.refresh(doc)
    db_session.refresh(parent_topic)
    db_session.refresh(child_topic)
    db_session.refresh(plan)

    assert len(user.courses) == 1
    assert len(user.attempts) == 1
    assert len(user.study_plans) == 1
    assert len(user.agent_runs) == 1
    assert len(course.documents) == 1
    assert len(course.topics) == 2
    assert len(doc.chunks) == 1
    assert len(doc.chunks[0].embedding) == 384
    assert child_topic.parent.id == parent_topic.id
    assert [t.id for t in parent_topic.subtopics] == [child_topic.id]
    assert len(child_topic.questions) == 1
    assert len(plan.items) == 1
    assert plan.items[0].topic.id == child_topic.id


# ---------------------------------------------------------------------------
# 4. Foreign Key, Unique & Check Constraints
# ---------------------------------------------------------------------------


def test_foreign_key_constraints_reject_invalid_references(db_session: Session) -> None:
    orphan_course = Course(
        user_id=uuid.uuid4(),
        title="Orphan Course",
        daily_minutes=60,
    )
    db_session.add(orphan_course)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    orphan_doc = Document(
        course_id=uuid.uuid4(),
        filename="ghost.pdf",
        file_path="/uploads/ghost.pdf",
    )
    db_session.add(orphan_doc)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_unique_constraints_prevent_duplicates(db_session: Session) -> None:
    user1 = _create_user(db_session, email="unique@example.com")

    # Duplicate email must fail
    duplicate_user = User(
        name="Clone",
        email="unique@example.com",
        password_hash="hash2",
    )
    db_session.add(duplicate_user)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    # Re-create clean user/course/topic for TopicMastery uniqueness check
    user1 = _create_user(db_session, email="mastery.user@example.com")
    course = _create_course(db_session, user1)
    topic = _create_topic(db_session, course, "Graphs")

    mastery1 = TopicMastery(
        user_id=user1.id,
        topic_id=topic.id,
        mastery_score=0.4,
        confidence_score=0.5,
    )
    db_session.add(mastery1)
    db_session.flush()

    duplicate_mastery = TopicMastery(
        user_id=user1.id,
        topic_id=topic.id,
        mastery_score=0.8,
        confidence_score=0.9,
    )
    db_session.add(duplicate_mastery)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_check_constraints_reject_invalid_domain_values(db_session: Session) -> None:
    user = _create_user(db_session, email="checks@example.com")

    invalid_course = Course(user_id=user.id, title="Bad Budget", daily_minutes=0)
    db_session.add(invalid_course)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    user = _create_user(db_session, email="checks2@example.com")
    course = _create_course(db_session, user)
    topic = _create_topic(db_session, course, "Dynamic Programming")

    invalid_mastery = TopicMastery(
        user_id=user.id,
        topic_id=topic.id,
        mastery_score=1.5,
        confidence_score=0.5,
    )
    db_session.add(invalid_mastery)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


# ---------------------------------------------------------------------------
# 5. Topic Prerequisite DAG & Cycle Prevention
# ---------------------------------------------------------------------------


def test_topic_prerequisite_valid_dag(db_session: Session) -> None:
    user = _create_user(db_session, email="dag@example.com")
    course = _create_course(db_session, user)

    arrays = _create_topic(db_session, course, "Arrays")
    recursion = _create_topic(db_session, course, "Recursion")
    trees = _create_topic(db_session, course, "Trees")
    graphs = _create_topic(db_session, course, "Graphs")

    # Trees requires Arrays & Recursion; Graphs requires Trees
    db_session.add_all(
        [
            TopicPrerequisite(topic_id=trees.id, prerequisite_id=arrays.id),
            TopicPrerequisite(topic_id=trees.id, prerequisite_id=recursion.id),
            TopicPrerequisite(topic_id=graphs.id, prerequisite_id=trees.id),
        ]
    )
    db_session.flush()

    db_session.refresh(trees)
    db_session.refresh(graphs)
    db_session.refresh(arrays)

    assert {t.id for t in trees.prerequisites} == {arrays.id, recursion.id}
    assert {t.id for t in graphs.prerequisites} == {trees.id}
    assert {t.id for t in arrays.dependents} == {trees.id}


def test_topic_self_prerequisite_is_rejected(db_session: Session) -> None:
    user = _create_user(db_session, email="self.prereq@example.com")
    course = _create_course(db_session, user)
    topic = _create_topic(db_session, course, "Recursion")

    db_session.add(TopicPrerequisite(topic_id=topic.id, prerequisite_id=topic.id))
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_direct_and_transitive_circular_prerequisites_are_rejected(db_session: Session) -> None:
    user = _create_user(db_session, email="cycle@example.com")
    course = _create_course(db_session, user)
    t_a = _create_topic(db_session, course, "Topic A")
    t_b = _create_topic(db_session, course, "Topic B")
    t_c = _create_topic(db_session, course, "Topic C")

    # Valid chain: C requires B, B requires A
    db_session.add(TopicPrerequisite(topic_id=t_b.id, prerequisite_id=t_a.id))
    db_session.add(TopicPrerequisite(topic_id=t_c.id, prerequisite_id=t_b.id))
    db_session.flush()

    # Direct cycle: A requires B (B -> A -> B)
    db_session.add(TopicPrerequisite(topic_id=t_a.id, prerequisite_id=t_b.id))
    with pytest.raises(CircularPrerequisiteError):
        db_session.flush()
    db_session.expunge_all()

    # Transitive 3-node cycle: A requires C (C -> B -> A -> C)
    db_session.add(TopicPrerequisite(topic_id=t_a.id, prerequisite_id=t_c.id))
    with pytest.raises(CircularPrerequisiteError):
        db_session.flush()
    db_session.rollback()


def test_cascading_deletes_remove_child_records(db_session: Session) -> None:
    user = _create_user(db_session, email="cascade@example.com")
    course = _create_course(db_session, user)
    doc = Document(course_id=course.id, filename="notes.pdf", file_path="/uploads/notes.pdf")
    db_session.add(doc)
    db_session.flush()

    chunk = DocumentChunk(document_id=doc.id, content="Chunk text", page_number=1)
    t1 = _create_topic(db_session, course, "Arrays")
    t2 = _create_topic(db_session, course, "Heaps")
    prereq = TopicPrerequisite(topic_id=t2.id, prerequisite_id=t1.id)
    plan = StudyPlan(user_id=user.id, course_id=course.id)
    db_session.add_all([chunk, prereq, plan])
    db_session.flush()

    item = PlanItem(
        plan_id=plan.id,
        topic_id=t1.id,
        scheduled_date=date(2026, 11, 21),
        duration_minutes=30,
    )
    db_session.add(item)
    db_session.flush()

    # Deleting the course should cascade across documents, chunks, topics, prerequisites, plans, items
    db_session.delete(course)
    db_session.flush()

    assert db_session.scalar(select(Document).where(Document.id == doc.id)) is None
    assert db_session.scalar(select(DocumentChunk).where(DocumentChunk.id == chunk.id)) is None
    assert db_session.scalar(select(Topic).where(Topic.id == t1.id)) is None
    assert db_session.scalar(select(StudyPlan).where(StudyPlan.id == plan.id)) is None
    assert db_session.scalar(select(PlanItem).where(PlanItem.id == item.id)) is None


def test_circular_prerequisite_rejected_within_same_flush(db_session: Session) -> None:
    user = _create_user(db_session, email="batch.cycle@example.com")
    course = _create_course(db_session, user)
    t_a = _create_topic(db_session, course, "Batch A")
    t_b = _create_topic(db_session, course, "Batch B")
    t_c = _create_topic(db_session, course, "Batch C")

    db_session.add_all(
        [
            TopicPrerequisite(topic_id=t_b.id, prerequisite_id=t_a.id),
            TopicPrerequisite(topic_id=t_c.id, prerequisite_id=t_b.id),
            TopicPrerequisite(topic_id=t_a.id, prerequisite_id=t_c.id),
        ]
    )
    with pytest.raises(CircularPrerequisiteError):
        db_session.flush()
    db_session.rollback()


def test_alembic_autogenerate_has_no_missing_tables_or_columns(test_engine: Engine) -> None:
    with test_engine.connect() as connection:
        mc = MigrationContext.configure(connection)
        diffs = compare_metadata(mc, Base.metadata)

    structural_diffs = [
        d for d in diffs if d[0] in {"add_table", "remove_table", "add_column", "remove_column"}
    ]
    assert structural_diffs == [], f"Unexpected schema drift: {structural_diffs}"
