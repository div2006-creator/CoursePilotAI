from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.document import Document

EMBEDDING_DIMENSIONS = 384


class DocumentChunk(Base):
    """Chunked document text and 384-dim pgvector embedding for RAG retrieval."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        CheckConstraint(
            "page_number IS NULL OR page_number >= 1",
            name="page_number_positive",
        ),
        CheckConstraint(
            "end_page_number IS NULL OR end_page_number >= 1",
            name="end_page_number_positive",
        ),
        CheckConstraint(
            "chunk_index >= 0",
            name="chunk_index_non_negative",
        ),
        Index("ix_document_chunks_doc_page", "document_id", "page_number"),
        Index("ix_document_chunks_doc_chunk_idx", "document_id", "chunk_index"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS),
        nullable=True,
    )

    # Relationships
    document: Mapped[Document] = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return (
            f"<DocumentChunk id={self.id} document_id={self.document_id} "
            f"chunk_index={self.chunk_index} page={self.page_number}>"
        )
