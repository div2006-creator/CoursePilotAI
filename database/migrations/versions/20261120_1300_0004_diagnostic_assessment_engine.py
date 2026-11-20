"""diagnostic_assessment_engine

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-20 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create diagnostic_sessions, session questions association, and link attempts."""
    # 1. diagnostic_sessions table
    op.create_table(
        "diagnostic_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("mode", sa.String(length=50), server_default="full", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="in_progress", nullable=False),
        sa.Column("total_questions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("correct_answers", sa.Integer(), server_default="0", nullable=False),
        sa.Column("score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('in_progress', 'completed', 'abandoned')",
            name=op.f("ck_diagnostic_sessions_status"),
        ),
        sa.CheckConstraint(
            "score >= 0.0 AND score <= 100.0",
            name=op.f("ck_diagnostic_sessions_score_range"),
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_diagnostic_sessions_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_diagnostic_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_diagnostic_sessions")),
    )
    op.create_index(
        "ix_diagnostic_sessions_course_status",
        "diagnostic_sessions",
        ["course_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_diagnostic_sessions_user_course",
        "diagnostic_sessions",
        ["user_id", "course_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_diagnostic_sessions_status"),
        "diagnostic_sessions",
        ["status"],
        unique=False,
    )

    # 2. diagnostic_session_questions table
    op.create_table(
        "diagnostic_session_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            name=op.f("fk_diagnostic_session_questions_question_id_questions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["diagnostic_sessions.id"],
            name=op.f("fk_diagnostic_session_questions_session_id_diagnostic_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_diagnostic_session_questions")),
    )
    op.create_index(
        "ix_diag_sess_q_session_order",
        "diagnostic_session_questions",
        ["session_id", "order"],
        unique=False,
    )

    # 3. Add diagnostic_session_id to attempts
    with op.batch_alter_table("attempts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("diagnostic_session_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            op.f("fk_attempts_diagnostic_session_id_diagnostic_sessions"),
            "diagnostic_sessions",
            ["diagnostic_session_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_attempts_diagnostic_session",
            ["diagnostic_session_id"],
            unique=False,
        )

    # 4. Add created_at to questions
    with op.batch_alter_table("questions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            )
        )


def downgrade() -> None:
    """Revert diagnostic assessment engine tables and columns."""
    with op.batch_alter_table("questions", schema=None) as batch_op:
        batch_op.drop_column("created_at")

    with op.batch_alter_table("attempts", schema=None) as batch_op:
        batch_op.drop_index("ix_attempts_diagnostic_session")
        batch_op.drop_constraint(
            op.f("fk_attempts_diagnostic_session_id_diagnostic_sessions"),
            type_="foreignkey",
        )
        batch_op.drop_column("diagnostic_session_id")

    op.drop_index("ix_diag_sess_q_session_order", table_name="diagnostic_session_questions")
    op.drop_table("diagnostic_session_questions")

    op.drop_index(op.f("ix_diagnostic_sessions_status"), table_name="diagnostic_sessions")
    op.drop_index("ix_diagnostic_sessions_user_course", table_name="diagnostic_sessions")
    op.drop_index("ix_diagnostic_sessions_course_status", table_name="diagnostic_sessions")
    op.drop_table("diagnostic_sessions")

