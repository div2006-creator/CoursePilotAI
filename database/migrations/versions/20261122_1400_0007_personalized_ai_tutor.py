"""personalized_ai_tutor

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-22 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tutor_sessions and tutor_messages tables and link attempts."""
    # 1. Create tutor_sessions table
    op.create_table(
        "tutor_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("plan_item_id", sa.Uuid(), nullable=True),
        sa.Column("language", sa.String(length=50), server_default="english", nullable=False),
        sa.Column("explanation_level", sa.String(length=50), server_default="intermediate", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="ACTIVE", nullable=False),
        sa.Column("current_stage", sa.String(length=50), server_default="DIAGNOSIS", nullable=False),
        sa.Column(
            "session_metadata",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'PAUSED', 'COMPLETED', 'active', 'paused', 'completed')",
            name="valid_tutor_session_status",
        ),
        sa.CheckConstraint(
            "current_stage IN ('DIAGNOSIS', 'EXPLANATION', 'EXAMPLE', 'PRACTICE', 'VERIFICATION', 'COMPLETED')",
            name="valid_tutor_session_stage",
        ),
        sa.CheckConstraint(
            "explanation_level IN ('beginner', 'intermediate', 'advanced')",
            name="valid_explanation_level",
        ),
        sa.CheckConstraint(
            "language IN ('english', 'hindi', 'hinglish')",
            name="valid_tutor_language",
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_item_id"], ["plan_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tutor_sessions_user_id"), "tutor_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_tutor_sessions_course_id"), "tutor_sessions", ["course_id"], unique=False)
    op.create_index(op.f("ix_tutor_sessions_topic_id"), "tutor_sessions", ["topic_id"], unique=False)
    op.create_index(op.f("ix_tutor_sessions_plan_item_id"), "tutor_sessions", ["plan_item_id"], unique=False)
    op.create_index(op.f("ix_tutor_sessions_status"), "tutor_sessions", ["status"], unique=False)
    op.create_index(op.f("ix_tutor_sessions_current_stage"), "tutor_sessions", ["current_stage"], unique=False)
    op.create_index(
        "ix_tutor_sessions_user_course", "tutor_sessions", ["user_id", "course_id"], unique=False
    )

    # 2. Create tutor_messages table
    op.create_table(
        "tutor_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("message_type", sa.String(length=50), server_default="chat", nullable=False),
        sa.Column("related_topic_id", sa.Uuid(), nullable=True),
        sa.Column("sources", sa.JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('USER', 'ASSISTANT', 'SYSTEM', 'user', 'assistant', 'system')",
            name="valid_tutor_message_role",
        ),
        sa.ForeignKeyConstraint(["related_topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["tutor_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tutor_messages_session_id"), "tutor_messages", ["session_id"], unique=False)
    op.create_index(op.f("ix_tutor_messages_type"), "tutor_messages", ["message_type"], unique=False)
    op.create_index(
        "ix_tutor_messages_session_created", "tutor_messages", ["session_id", "created_at"], unique=False
    )

    # 3. Add tutor_session_id to attempts table
    with op.batch_alter_table("attempts") as batch_op:
        batch_op.add_column(sa.Column("tutor_session_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_attempts_tutor_session",
            "tutor_sessions",
            ["tutor_session_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_attempts_tutor_session", ["tutor_session_id"], unique=False)


def downgrade() -> None:
    """Drop tutor_messages, tutor_sessions, and remove tutor_session_id from attempts."""
    with op.batch_alter_table("attempts") as batch_op:
        batch_op.drop_index("ix_attempts_tutor_session")
        batch_op.drop_constraint("fk_attempts_tutor_session", type_="foreignkey")
        batch_op.drop_column("tutor_session_id")

    op.drop_index("ix_tutor_messages_session_created", table_name="tutor_messages")
    op.drop_index(op.f("ix_tutor_messages_type"), table_name="tutor_messages")
    op.drop_index(op.f("ix_tutor_messages_session_id"), table_name="tutor_messages")
    op.drop_table("tutor_messages")

    op.drop_index("ix_tutor_sessions_user_course", table_name="tutor_sessions")
    op.drop_index(op.f("ix_tutor_sessions_current_stage"), table_name="tutor_sessions")
    op.drop_index(op.f("ix_tutor_sessions_status"), table_name="tutor_sessions")
    op.drop_index(op.f("ix_tutor_sessions_plan_item_id"), table_name="tutor_sessions")
    op.drop_index(op.f("ix_tutor_sessions_topic_id"), table_name="tutor_sessions")
    op.drop_index(op.f("ix_tutor_sessions_course_id"), table_name="tutor_sessions")
    op.drop_index(op.f("ix_tutor_sessions_user_id"), table_name="tutor_sessions")
    op.drop_table("tutor_sessions")
