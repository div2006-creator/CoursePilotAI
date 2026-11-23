from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
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
    from app.models.course import Course
    from app.models.topic import Topic
    from app.models.user import User


class TopicMasteryHistory(Base):
    """Historical snapshot of a student's topic mastery score for longitudinal progress tracking."""

    __tablename__ = "topic_mastery_history"
    __table_args__ = (
        CheckConstraint(
            "mastery_score >= 0.0 AND mastery_score <= 1.0",
            name="ck_mastery_history_score_range",
        ),
        CheckConstraint(
            "confidence_score >= 0.0 AND confidence_score <= 1.0",
            name="ck_mastery_history_confidence_range",
        ),
        CheckConstraint(
            "evidence_count >= 0",
            name="ck_mastery_history_evidence_count_positive",
        ),
        Index("ix_mastery_hist_user_course_recorded", "user_id", "course_id", "recorded_at"),
        Index("ix_mastery_hist_user_topic_recorded", "user_id", "topic_id", "recorded_at"),
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
    mastery_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0.0",
    )
    evidence_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    assessment_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="DIAGNOSTIC",
        server_default="DIAGNOSTIC",
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.current_timestamp(),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="mastery_histories")
    course: Mapped[Course] = relationship("Course", back_populates="mastery_histories")
    topic: Mapped[Topic] = relationship("Topic", back_populates="mastery_histories")

    def __repr__(self) -> str:
        return (
            f"<TopicMasteryHistory id={self.id} topic_id={self.topic_id} "
            f"score={self.mastery_score} type={self.assessment_type}>"
        )

