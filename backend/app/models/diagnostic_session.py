"""Diagnostic assessment session models and question linkage."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utc_now

if TYPE_CHECKING:
    from app.models.attempt import Attempt
    from app.models.course import Course
    from app.models.question import Question
    from app.models.user import User


class DiagnosticSession(Base):
    """An interactive diagnostic assessment run evaluating student topic knowledge."""

    __tablename__ = "diagnostic_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'abandoned')",
            name="ck_diagnostic_sessions_status",
        ),
        CheckConstraint(
            "score >= 0.0 AND score <= 100.0",
            name="ck_diagnostic_sessions_score_range",
        ),
        Index("ix_diagnostic_sessions_user_course", "user_id", "course_id"),
        Index("ix_diagnostic_sessions_course_status", "course_id", "status"),
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
    mode: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="full",
        server_default="full",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="in_progress",
        server_default="in_progress",
        index=True,
    )
    total_questions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    correct_answers: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0.0",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.current_timestamp(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.current_timestamp(),
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="diagnostic_sessions")
    course: Mapped[Course] = relationship("Course", back_populates="diagnostic_sessions")
    attempts: Mapped[list[Attempt]] = relationship(
        "Attempt",
        back_populates="diagnostic_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    session_questions: Mapped[list[DiagnosticSessionQuestion]] = relationship(
        "DiagnosticSessionQuestion",
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DiagnosticSessionQuestion.order",
    )

    def __repr__(self) -> str:
        return (
            f"<DiagnosticSession id={self.id} course_id={self.course_id} "
            f"status={self.status!r} score={self.score}>"
        )


class DiagnosticSessionQuestion(Base):
    """Associates a specific question instance and question ordering to a diagnostic session."""

    __tablename__ = "diagnostic_session_questions"
    __table_args__ = (
        Index("ix_diag_sess_q_session_order", "session_id", "order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.current_timestamp(),
        nullable=False,
    )

    # Relationships
    session: Mapped[DiagnosticSession] = relationship(
        "DiagnosticSession",
        back_populates="session_questions",
    )
    question: Mapped[Question] = relationship(
        "Question",
        back_populates="session_questions",
    )

    def __repr__(self) -> str:
        return f"<DiagnosticSessionQuestion session_id={self.session_id} question_id={self.question_id} order={self.order}>"

