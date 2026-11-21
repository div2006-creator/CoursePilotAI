from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utc_now

if TYPE_CHECKING:
    from app.models.attempt import Attempt
    from app.models.diagnostic_session import DiagnosticSession
    from app.models.document import Document
    from app.models.knowledge_gap import KnowledgeGapAnalysis
    from app.models.study_plan import StudyPlan
    from app.models.topic import Topic
    from app.models.user import User


class Course(Base):
    """Academic course enrolled in or uploaded by a learner."""

    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint("daily_minutes > 0", name="daily_minutes_positive"),
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
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    exam_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    daily_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
        server_default="60",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.current_timestamp(),
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="courses")
    documents: Mapped[list[Document]] = relationship(
        "Document",
        back_populates="course",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    topics: Mapped[list[Topic]] = relationship(
        "Topic",
        back_populates="course",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    attempts: Mapped[list[Attempt]] = relationship(
        "Attempt",
        back_populates="course",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    study_plans: Mapped[list[StudyPlan]] = relationship(
        "StudyPlan",
        back_populates="course",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    diagnostic_sessions: Mapped[list[DiagnosticSession]] = relationship(
        "DiagnosticSession",
        back_populates="course",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    knowledge_gap_analyses: Mapped[list[KnowledgeGapAnalysis]] = relationship(
        "KnowledgeGapAnalysis",
        back_populates="course",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Course id={self.id} title={self.title!r}>"
