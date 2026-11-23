"""learning_analytics

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-22 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, Sequence[str], None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create topic_mastery_history table for longitudinal learning analytics."""
    op.create_table(
        "topic_mastery_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("mastery_score", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("evidence_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("assessment_type", sa.String(length=50), server_default="DIAGNOSTIC", nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "mastery_score >= 0.0 AND mastery_score <= 1.0",
            name="ck_mastery_history_score_range",
        ),
        sa.CheckConstraint(
            "confidence_score >= 0.0 AND confidence_score <= 1.0",
            name="ck_mastery_history_confidence_range",
        ),
        sa.CheckConstraint(
            "evidence_count >= 0",
            name="ck_mastery_history_evidence_count_positive",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_topic_mastery_history_user_id"),
        "topic_mastery_history",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_topic_mastery_history_course_id"),
        "topic_mastery_history",
        ["course_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_topic_mastery_history_topic_id"),
        "topic_mastery_history",
        ["topic_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_topic_mastery_history_recorded_at"),
        "topic_mastery_history",
        ["recorded_at"],
        unique=False,
    )
    op.create_index(
        "ix_mastery_hist_user_course_recorded",
        "topic_mastery_history",
        ["user_id", "course_id", "recorded_at"],
        unique=False,
    )
    op.create_index(
        "ix_mastery_hist_user_topic_recorded",
        "topic_mastery_history",
        ["user_id", "topic_id", "recorded_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop topic_mastery_history table."""
    op.drop_index("ix_mastery_hist_user_topic_recorded", table_name="topic_mastery_history")
    op.drop_index("ix_mastery_hist_user_course_recorded", table_name="topic_mastery_history")
    op.drop_index(op.f("ix_topic_mastery_history_recorded_at"), table_name="topic_mastery_history")
    op.drop_index(op.f("ix_topic_mastery_history_topic_id"), table_name="topic_mastery_history")
    op.drop_index(op.f("ix_topic_mastery_history_course_id"), table_name="topic_mastery_history")
    op.drop_index(op.f("ix_topic_mastery_history_user_id"), table_name="topic_mastery_history")
    op.drop_table("topic_mastery_history")

