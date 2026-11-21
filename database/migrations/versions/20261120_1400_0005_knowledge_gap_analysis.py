"""knowledge_gap_analysis

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-20 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create knowledge_gap_analyses and knowledge_gaps tables."""
    # 1. knowledge_gap_analyses table
    op.create_table(
        "knowledge_gap_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("diagnostic_session_id", sa.Uuid(), nullable=True),
        sa.Column(
            "analysis_data",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=False,
        ),
        sa.Column("overall_gap_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="completed", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "overall_gap_score >= 0.0 AND overall_gap_score <= 100.0",
            name=op.f("ck_knowledge_gap_analyses_ck_kg_analysis_score_range"),
        ),
        sa.CheckConstraint(
            "status IN ('completed', 'archived')",
            name=op.f("ck_knowledge_gap_analyses_ck_kg_analysis_status"),
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_knowledge_gap_analyses_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["diagnostic_session_id"],
            ["diagnostic_sessions.id"],
            name=op.f("fk_knowledge_gap_analyses_diagnostic_session_id_diagnostic_sessions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_knowledge_gap_analyses_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_gap_analyses")),
    )
    op.create_index(
        op.f("ix_knowledge_gap_analyses_course_id"),
        "knowledge_gap_analyses",
        ["course_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_gap_analyses_diagnostic_session_id"),
        "knowledge_gap_analyses",
        ["diagnostic_session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_gap_analyses_user_id"),
        "knowledge_gap_analyses",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_gap_analyses_status"),
        "knowledge_gap_analyses",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_kg_analysis_user_course",
        "knowledge_gap_analyses",
        ["user_id", "course_id"],
        unique=False,
    )
    op.create_index(
        "ix_kg_analysis_created",
        "knowledge_gap_analyses",
        ["created_at"],
        unique=False,
    )

    # 2. knowledge_gaps table
    op.create_table(
        "knowledge_gaps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("gap_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column(
            "evidence",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=True,
        ),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "severity >= 0.0 AND severity <= 100.0",
            name=op.f("ck_knowledge_gaps_ck_kg_severity_range"),
        ),
        sa.CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name=op.f("ck_knowledge_gaps_ck_kg_confidence_range"),
        ),
        sa.CheckConstraint(
            "gap_type IN ('direct_weakness', 'foundational_weakness', 'potential_knowledge_gap', 'isolated_difficulty')",
            name=op.f("ck_knowledge_gaps_ck_kg_gap_type"),
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["knowledge_gap_analyses.id"],
            name=op.f("fk_knowledge_gaps_analysis_id_knowledge_gap_analyses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            name=op.f("fk_knowledge_gaps_topic_id_topics"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_gaps")),
    )
    op.create_index(
        op.f("ix_knowledge_gaps_analysis_id"),
        "knowledge_gaps",
        ["analysis_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_gaps_gap_type"),
        "knowledge_gaps",
        ["gap_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_gaps_topic_id"),
        "knowledge_gaps",
        ["topic_id"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_gaps_analysis_type",
        "knowledge_gaps",
        ["analysis_id", "gap_type"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_gaps_topic",
        "knowledge_gaps",
        ["topic_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop knowledge_gaps and knowledge_gap_analyses tables."""
    op.drop_table("knowledge_gaps")
    op.drop_table("knowledge_gap_analyses")

