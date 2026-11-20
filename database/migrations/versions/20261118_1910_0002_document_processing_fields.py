"""document_processing_fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-18 19:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add document processing metadata and chunk ordering/page-range fields."""
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.add_column(sa.Column("file_size", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("page_count", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("extracted_text_length", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("error_message", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=50),
            server_default="uploaded",
            existing_nullable=False,
        )

    with op.batch_alter_table("document_chunks", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("chunk_index", sa.Integer(), server_default="0", nullable=False)
        )
        batch_op.add_column(sa.Column("end_page_number", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("token_count", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(
            "end_page_number_positive",
            "end_page_number IS NULL OR end_page_number >= 1",
        )
        batch_op.create_check_constraint(
            "chunk_index_non_negative",
            "chunk_index >= 0",
        )
        batch_op.create_index(
            "ix_document_chunks_doc_chunk_idx",
            ["document_id", "chunk_index"],
            unique=False,
        )


def downgrade() -> None:
    """Revert document processing metadata and chunk ordering/page-range fields."""
    with op.batch_alter_table("document_chunks", schema=None) as batch_op:
        batch_op.drop_index("ix_document_chunks_doc_chunk_idx")
        batch_op.drop_constraint("chunk_index_non_negative", type_="check")
        batch_op.drop_constraint("end_page_number_positive", type_="check")
        batch_op.drop_column("token_count")
        batch_op.drop_column("end_page_number")
        batch_op.drop_column("chunk_index")

    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=50),
            server_default="pending",
            existing_nullable=False,
        )
        batch_op.drop_column("processed_at")
        batch_op.drop_column("error_message")
        batch_op.drop_column("extracted_text_length")
        batch_op.drop_column("page_count")
        batch_op.drop_column("file_size")

