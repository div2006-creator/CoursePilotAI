from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utc_now

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.diagnostic_session import DiagnosticSession
    from app.models.question import Question
    from app.models.topic import Topic
    from app.models.tutor_session import TutorSession
    from app.models.user import User


class Attempt(Base):
    """Learner response record for a diagnostic or practice question."""

    __tablename__ = "attempts"
    __table_args__ = (
        CheckConstraint("time_taken >= 0", name="time_taken_non_negative"),
        Index("ix_attempts_user_course", "user_id", "course_id"),
        Index("ix_attempts_user_topic", "user_id", "topic_id"),
        Index("ix_attempts_diagnostic_session", "diagnostic_session_id"),
        Index("ix_attempts_tutor_session", "tutor_session_id"),
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
    topic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    diagnostic_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("diagnostic_sessions.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    tutor_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tutor_sessions.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    selected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    time_taken: Mapped[int] = mapped_column(
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
        index=True,
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="attempts")
    course: Mapped[Course] = relationship("Course", back_populates="attempts")
    topic: Mapped[Topic] = relationship("Topic", back_populates="attempts")
    question: Mapped[Question] = relationship("Question", back_populates="attempts")
    diagnostic_session: Mapped[Optional[DiagnosticSession]] = relationship(
        "DiagnosticSession",
        back_populates="attempts",
    )
    tutor_session: Mapped[Optional[TutorSession]] = relationship(
        "TutorSession",
        back_populates="attempts",
    )

    def __repr__(self) -> str:
        return (
            f"<Attempt id={self.id} user_id={self.user_id} "
            f"question_id={self.question_id} is_correct={self.is_correct}>"
        )
