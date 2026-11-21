"""SQLAlchemy models for Knowledge Gap Analysis and Prerequisite Intelligence."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utc_now

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.diagnostic_session import DiagnosticSession
    from app.models.topic import Topic
    from app.models.user import User


class KnowledgeGapAnalysis(Base):
    """A comprehensive snapshot of a student's knowledge gaps for a course."""

    __tablename__ = "knowledge_gap_analyses"
    __table_args__ = (
        CheckConstraint(
            "overall_gap_score >= 0.0 AND overall_gap_score <= 100.0",
            name="ck_kg_analysis_score_range",
        ),
        CheckConstraint(
            "status IN ('completed', 'archived')",
            name="ck_kg_analysis_status",
        ),
        Index("ix_kg_analysis_user_course", "user_id", "course_id"),
        Index("ix_kg_analysis_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    diagnostic_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("diagnostic_sessions.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    analysis_data: Mapped[Any] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=False,
    )
    overall_gap_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0.0",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="completed",
        server_default="completed",
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.current_timestamp(),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="knowledge_gap_analyses")
    course: Mapped[Course] = relationship("Course", back_populates="knowledge_gap_analyses")
    diagnostic_session: Mapped[Optional[DiagnosticSession]] = relationship("DiagnosticSession")
    gaps: Mapped[list[KnowledgeGap]] = relationship(
        "KnowledgeGap",
        back_populates="analysis",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="desc(KnowledgeGap.severity)",
    )

    def __repr__(self) -> str:
        return (
            f"<KnowledgeGapAnalysis id={self.id} course_id={self.course_id} "
            f"score={self.overall_gap_score:.1f}>"
        )


class KnowledgeGap(Base):
    """Individual identified topic knowledge gap with causal evidence and severity."""

    __tablename__ = "knowledge_gaps"
    __table_args__ = (
        CheckConstraint(
            "severity >= 0.0 AND severity <= 100.0",
            name="ck_kg_severity_range",
        ),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_kg_confidence_range",
        ),
        CheckConstraint(
            "gap_type IN ('direct_weakness', 'foundational_weakness', 'potential_knowledge_gap', 'isolated_difficulty')",
            name="ck_kg_gap_type",
        ),
        Index("ix_knowledge_gaps_analysis_type", "analysis_id", "gap_type"),
        Index("ix_knowledge_gaps_topic", "topic_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_gap_analyses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    gap_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    severity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0.0",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
        server_default="1.0",
    )
    evidence: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True,
    )
    recommendation: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.current_timestamp(),
        nullable=False,
    )

    # Relationships
    analysis: Mapped[KnowledgeGapAnalysis] = relationship(
        "KnowledgeGapAnalysis",
        back_populates="gaps",
    )
    topic: Mapped[Topic] = relationship("Topic")

    def __repr__(self) -> str:
        return (
            f"<KnowledgeGap id={self.id} topic_id={self.topic_id} "
            f"type={self.gap_type!r} severity={self.severity:.1f}>"
        )

