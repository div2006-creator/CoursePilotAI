"""topic_extraction_and_knowledge_graph

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-19 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unit, source tracking, timestamps, constraints, and prerequisite confidence/reason."""
    is_postgres = op.get_context().dialect.name == "postgresql"
    json_col = postgresql.JSONB(astext_type=sa.Text()) if is_postgres else sa.JSON()

    with op.batch_alter_table("topics", schema=None) as batch_op:
        batch_op.add_column(sa.Column("unit_name", sa.String(length=100), nullable=True))
        batch_op.add_column(
            sa.Column(
                "source_type",
                sa.String(length=50),
                server_default="explicit",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("source_pages", json_col, nullable=True))
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            )
        )
        batch_op.create_unique_constraint(
            "uq_topics_course_name_parent",
            ["course_id", "name", "parent_id"],
        )
        batch_op.create_index(
            "ix_topics_course_unit",
            ["course_id", "unit_name"],
            unique=False,
        )
        batch_op.create_index(
            "ix_topics_unit_name",
            ["unit_name"],
            unique=False,
        )

    with op.batch_alter_table("topic_prerequisites", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False)
        )
        batch_op.add_column(sa.Column("reason", sa.Text(), nullable=True))
        batch_op.create_check_constraint(
            "ck_topic_prerequisites_confidence_range",
            "confidence >= 0.0 AND confidence <= 1.0",
        )


def downgrade() -> None:
    """Revert topic extraction and knowledge graph schema additions."""
    with op.batch_alter_table("topic_prerequisites", schema=None) as batch_op:
        batch_op.drop_constraint("ck_topic_prerequisites_confidence_range", type_="check")
        batch_op.drop_column("reason")
        batch_op.drop_column("confidence")

    with op.batch_alter_table("topics", schema=None) as batch_op:
        batch_op.drop_index("ix_topics_unit_name")
        batch_op.drop_index("ix_topics_course_unit")
        batch_op.drop_constraint("uq_topics_course_name_parent", type_="unique")
        batch_op.drop_column("created_at")
        batch_op.drop_column("source_pages")
        batch_op.drop_column("source_type")
        batch_op.drop_column("unit_name")

