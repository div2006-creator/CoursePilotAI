"""initial_schema

Revision ID: 0001
Revises:
Create Date: 2026-11-18 03:22:00.000000

"""
from typing import Sequence, Union

from alembic import op
import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create pgvector extension and all CoursePilot AI initial tables."""
    # Ensure pgvector extension is enabled before creating VECTOR(384) columns
    if op.get_context().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 1. users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # 2. agent_runs
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("task_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("input_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_agent_runs_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_runs")),
    )
    op.create_index(op.f("ix_agent_runs_created_at"), "agent_runs", ["created_at"], unique=False)
    op.create_index(op.f("ix_agent_runs_status"), "agent_runs", ["status"], unique=False)
    op.create_index(op.f("ix_agent_runs_task_type"), "agent_runs", ["task_type"], unique=False)
    op.create_index(op.f("ix_agent_runs_user_id"), "agent_runs", ["user_id"], unique=False)
    op.create_index(
        "ix_agent_runs_user_task_created",
        "agent_runs",
        ["user_id", "task_type", "created_at"],
        unique=False,
    )

    # 3. courses
    op.create_table(
        "courses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("exam_date", sa.Date(), nullable=True),
        sa.Column("daily_minutes", sa.Integer(), server_default="60", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("daily_minutes > 0", name=op.f("ck_courses_daily_minutes_positive")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_courses_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_courses")),
    )
    op.create_index(op.f("ix_courses_exam_date"), "courses", ["exam_date"], unique=False)
    op.create_index(op.f("ix_courses_user_id"), "courses", ["user_id"], unique=False)

    # 4. documents
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_documents_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
    )
    op.create_index(op.f("ix_documents_course_id"), "documents", ["course_id"], unique=False)
    op.create_index("ix_documents_course_status", "documents", ["course_id", "status"], unique=False)
    op.create_index(op.f("ix_documents_status"), "documents", ["status"], unique=False)

    # 5. study_plans
    op.create_table(
        "study_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="active", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("version >= 1", name=op.f("ck_study_plans_version_positive")),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_study_plans_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_study_plans_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_study_plans")),
    )
    op.create_index(op.f("ix_study_plans_course_id"), "study_plans", ["course_id"], unique=False)
    op.create_index(op.f("ix_study_plans_status"), "study_plans", ["status"], unique=False)
    op.create_index(
        "ix_study_plans_user_course_status",
        "study_plans",
        ["user_id", "course_id", "status"],
        unique=False,
    )
    op.create_index(op.f("ix_study_plans_user_id"), "study_plans", ["user_id"], unique=False)

    # 6. topics
    op.create_table(
        "topics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.String(length=50), server_default="beginner", nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "parent_id IS NULL OR parent_id <> id",
            name=op.f("ck_topics_no_self_parent"),
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_topics_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["topics.id"],
            name=op.f("fk_topics_parent_id_topics"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topics")),
    )
    op.create_index("ix_topics_course_difficulty", "topics", ["course_id", "difficulty"], unique=False)
    op.create_index(op.f("ix_topics_course_id"), "topics", ["course_id"], unique=False)
    op.create_index("ix_topics_course_name", "topics", ["course_id", "name"], unique=False)
    op.create_index(op.f("ix_topics_difficulty"), "topics", ["difficulty"], unique=False)
    op.create_index(op.f("ix_topics_name"), "topics", ["name"], unique=False)
    op.create_index(op.f("ix_topics_parent_id"), "topics", ["parent_id"], unique=False)

    # 7. document_chunks (with pgvector 384-dim embedding)
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("embedding", pgvector.sqlalchemy.vector.VECTOR(dim=384), nullable=True),
        sa.CheckConstraint(
            "page_number IS NULL OR page_number >= 1",
            name=op.f("ck_document_chunks_page_number_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_document_chunks_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_chunks")),
    )
    op.create_index(
        "ix_document_chunks_doc_page",
        "document_chunks",
        ["document_id", "page_number"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_chunks_document_id"),
        "document_chunks",
        ["document_id"],
        unique=False,
    )

    # 8. plan_items
    op.create_table(
        "plan_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.CheckConstraint(
            "duration_minutes > 0",
            name=op.f("ck_plan_items_duration_minutes_positive"),
        ),
        sa.CheckConstraint("priority >= 1", name=op.f("ck_plan_items_priority_positive")),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["study_plans.id"],
            name=op.f("fk_plan_items_plan_id_study_plans"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            name=op.f("fk_plan_items_topic_id_topics"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plan_items")),
    )
    op.create_index("ix_plan_items_plan_date", "plan_items", ["plan_id", "scheduled_date"], unique=False)
    op.create_index(op.f("ix_plan_items_plan_id"), "plan_items", ["plan_id"], unique=False)
    op.create_index(op.f("ix_plan_items_scheduled_date"), "plan_items", ["scheduled_date"], unique=False)
    op.create_index(op.f("ix_plan_items_status"), "plan_items", ["status"], unique=False)
    op.create_index(op.f("ix_plan_items_topic_id"), "plan_items", ["topic_id"], unique=False)

    # 9. questions
    op.create_table(
        "questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("correct_answer", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.String(length=50), server_default="medium", nullable=False),
        sa.Column("source", sa.String(length=100), server_default="seed", nullable=False),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            name=op.f("fk_questions_topic_id_topics"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_questions")),
    )
    op.create_index(op.f("ix_questions_difficulty"), "questions", ["difficulty"], unique=False)
    op.create_index(op.f("ix_questions_source"), "questions", ["source"], unique=False)
    op.create_index(
        "ix_questions_topic_difficulty",
        "questions",
        ["topic_id", "difficulty"],
        unique=False,
    )
    op.create_index(op.f("ix_questions_topic_id"), "questions", ["topic_id"], unique=False)

    # 10. topic_mastery
    op.create_table(
        "topic_mastery",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("mastery_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("confidence_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("last_assessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "confidence_score >= 0.0 AND confidence_score <= 1.0",
            name=op.f("ck_topic_mastery_confidence_score_range"),
        ),
        sa.CheckConstraint(
            "mastery_score >= 0.0 AND mastery_score <= 1.0",
            name=op.f("ck_topic_mastery_mastery_score_range"),
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            name=op.f("fk_topic_mastery_topic_id_topics"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_topic_mastery_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topic_mastery")),
        sa.UniqueConstraint("user_id", "topic_id", name="uq_topic_mastery_user_topic"),
    )
    op.create_index(op.f("ix_topic_mastery_topic_id"), "topic_mastery", ["topic_id"], unique=False)
    op.create_index(op.f("ix_topic_mastery_user_id"), "topic_mastery", ["user_id"], unique=False)

    # 11. topic_prerequisites
    op.create_table(
        "topic_prerequisites",
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("prerequisite_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "topic_id <> prerequisite_id",
            name=op.f("ck_topic_prerequisites_no_self_prerequisite"),
        ),
        sa.ForeignKeyConstraint(
            ["prerequisite_id"],
            ["topics.id"],
            name=op.f("fk_topic_prerequisites_prerequisite_id_topics"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            name=op.f("fk_topic_prerequisites_topic_id_topics"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("topic_id", "prerequisite_id", name=op.f("pk_topic_prerequisites")),
    )
    op.create_index(
        "ix_topic_prerequisites_prerequisite_id",
        "topic_prerequisites",
        ["prerequisite_id"],
        unique=False,
    )

    # 12. attempts
    op.create_table(
        "attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("selected_answer", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("time_taken", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("time_taken >= 0", name=op.f("ck_attempts_time_taken_non_negative")),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_attempts_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            name=op.f("fk_attempts_question_id_questions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            name=op.f("fk_attempts_topic_id_topics"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_attempts_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attempts")),
    )
    op.create_index(op.f("ix_attempts_course_id"), "attempts", ["course_id"], unique=False)
    op.create_index(op.f("ix_attempts_created_at"), "attempts", ["created_at"], unique=False)
    op.create_index(op.f("ix_attempts_is_correct"), "attempts", ["is_correct"], unique=False)
    op.create_index(op.f("ix_attempts_question_id"), "attempts", ["question_id"], unique=False)
    op.create_index(op.f("ix_attempts_topic_id"), "attempts", ["topic_id"], unique=False)
    op.create_index("ix_attempts_user_course", "attempts", ["user_id", "course_id"], unique=False)
    op.create_index(op.f("ix_attempts_user_id"), "attempts", ["user_id"], unique=False)
    op.create_index("ix_attempts_user_topic", "attempts", ["user_id", "topic_id"], unique=False)


def downgrade() -> None:
    """Drop all CoursePilot AI tables in reverse dependency order."""
    op.drop_index("ix_attempts_user_topic", table_name="attempts")
    op.drop_index(op.f("ix_attempts_user_id"), table_name="attempts")
    op.drop_index("ix_attempts_user_course", table_name="attempts")
    op.drop_index(op.f("ix_attempts_topic_id"), table_name="attempts")
    op.drop_index(op.f("ix_attempts_question_id"), table_name="attempts")
    op.drop_index(op.f("ix_attempts_is_correct"), table_name="attempts")
    op.drop_index(op.f("ix_attempts_created_at"), table_name="attempts")
    op.drop_index(op.f("ix_attempts_course_id"), table_name="attempts")
    op.drop_table("attempts")

    op.drop_index("ix_topic_prerequisites_prerequisite_id", table_name="topic_prerequisites")
    op.drop_table("topic_prerequisites")

    op.drop_index(op.f("ix_topic_mastery_user_id"), table_name="topic_mastery")
    op.drop_index(op.f("ix_topic_mastery_topic_id"), table_name="topic_mastery")
    op.drop_table("topic_mastery")

    op.drop_index(op.f("ix_questions_topic_id"), table_name="questions")
    op.drop_index("ix_questions_topic_difficulty", table_name="questions")
    op.drop_index(op.f("ix_questions_source"), table_name="questions")
    op.drop_index(op.f("ix_questions_difficulty"), table_name="questions")
    op.drop_table("questions")

    op.drop_index(op.f("ix_plan_items_topic_id"), table_name="plan_items")
    op.drop_index(op.f("ix_plan_items_status"), table_name="plan_items")
    op.drop_index(op.f("ix_plan_items_scheduled_date"), table_name="plan_items")
    op.drop_index(op.f("ix_plan_items_plan_id"), table_name="plan_items")
    op.drop_index("ix_plan_items_plan_date", table_name="plan_items")
    op.drop_table("plan_items")

    op.drop_index(op.f("ix_document_chunks_document_id"), table_name="document_chunks")
    op.drop_index("ix_document_chunks_doc_page", table_name="document_chunks")
    op.drop_table("document_chunks")

    op.drop_index(op.f("ix_topics_parent_id"), table_name="topics")
    op.drop_index(op.f("ix_topics_name"), table_name="topics")
    op.drop_index(op.f("ix_topics_difficulty"), table_name="topics")
    op.drop_index("ix_topics_course_name", table_name="topics")
    op.drop_index(op.f("ix_topics_course_id"), table_name="topics")
    op.drop_index("ix_topics_course_difficulty", table_name="topics")
    op.drop_table("topics")

    op.drop_index(op.f("ix_study_plans_user_id"), table_name="study_plans")
    op.drop_index("ix_study_plans_user_course_status", table_name="study_plans")
    op.drop_index(op.f("ix_study_plans_status"), table_name="study_plans")
    op.drop_index(op.f("ix_study_plans_course_id"), table_name="study_plans")
    op.drop_table("study_plans")

    op.drop_index(op.f("ix_documents_status"), table_name="documents")
    op.drop_index("ix_documents_course_status", table_name="documents")
    op.drop_index(op.f("ix_documents_course_id"), table_name="documents")
    op.drop_table("documents")

    op.drop_index(op.f("ix_courses_user_id"), table_name="courses")
    op.drop_index(op.f("ix_courses_exam_date"), table_name="courses")
    op.drop_table("courses")

    op.drop_index("ix_agent_runs_user_task_created", table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_user_id"), table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_task_type"), table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_status"), table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_created_at"), table_name="agent_runs")
    op.drop_table("agent_runs")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
