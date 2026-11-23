"""adaptive_learning_planner

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add adaptive learning planner columns and constraints to study_plans and plan_items."""
    # 1. Update study_plans table
    with op.batch_alter_table("study_plans") as batch_op:
        batch_op.add_column(
            sa.Column("daily_minutes", sa.Integer(), server_default="60", nullable=False)
        )
        batch_op.add_column(
            sa.Column("exam_date", sa.Date(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("summary", sa.Text(), nullable=True)
        )
        batch_op.create_index(
            op.f("ix_study_plans_exam_date"), ["exam_date"], unique=False
        )

    # 2. Update plan_items table
    with op.batch_alter_table("plan_items") as batch_op:
        batch_op.add_column(
            sa.Column("priority_score", sa.Float(), server_default="0.0", nullable=False)
        )
        batch_op.add_column(
            sa.Column("session_type", sa.String(length=50), server_default="LEARN", nullable=False)
        )
        batch_op.add_column(
            sa.Column("sequence_number", sa.Integer(), server_default="1", nullable=False)
        )
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_index(
            op.f("ix_plan_items_session_type"), ["session_type"], unique=False
        )
        batch_op.create_index(
            "ix_plan_items_sequence", ["plan_id", "sequence_number"], unique=False
        )
        batch_op.create_check_constraint(
            "priority_score_range", "priority_score >= 0.0 AND priority_score <= 100.0"
        )
        batch_op.create_check_constraint(
            "sequence_number_positive", "sequence_number >= 1"
        )
        batch_op.create_check_constraint(
            "valid_session_type",
            "session_type IN ('LEARN', 'PRACTICE', 'REVISION', 'ASSESSMENT')",
        )


def downgrade() -> None:
    """Revert adaptive learning planner additions."""
    with op.batch_alter_table("plan_items") as batch_op:
        batch_op.drop_constraint("valid_session_type", type_="check")
        batch_op.drop_constraint("sequence_number_positive", type_="check")
        batch_op.drop_constraint("priority_score_range", type_="check")
        batch_op.drop_index("ix_plan_items_sequence")
        batch_op.drop_index(op.f("ix_plan_items_session_type"))
        batch_op.drop_column("completed_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("sequence_number")
        batch_op.drop_column("session_type")
        batch_op.drop_column("priority_score")

    with op.batch_alter_table("study_plans") as batch_op:
        batch_op.drop_index(op.f("ix_study_plans_exam_date"))
        batch_op.drop_column("summary")
        batch_op.drop_column("exam_date")
        batch_op.drop_column("daily_minutes")

