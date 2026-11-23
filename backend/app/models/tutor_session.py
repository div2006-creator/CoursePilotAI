"""TutorSession ORM model for Part 10: Personalized AI Tutor."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utc_now

if TYPE_CHECKING:
    from app.models.attempt import Attempt
    from app.models.course import Course
    from app.models.plan_item import PlanItem
    from app.models.topic import Topic
    from app.models.tutor_message import TutorMessage
    from app.models.user import User

# Valid status states
STATUS_ACTIVE = "ACTIVE"
STATUS_PAUSED = "PAUSED"
STATUS_COMPLETED = "COMPLETED"

# Valid teaching stages
STAGE_DIAGNOSIS = "DIAGNOSIS"
STAGE_EXPLANATION = "EXPLANATION"
STAGE_EXAMPLE = "EXAMPLE"
STAGE_PRACTICE = "PRACTICE"
STAGE_VERIFICATION = "VERIFICATION"
STAGE_COMPLETED = "COMPLETED"

VALID_STAGES = (
    STAGE_DIAGNOSIS,
    STAGE_EXPLANATION,
    STAGE_EXAMPLE,
    STAGE_PRACTICE,
    STAGE_VERIFICATION,
    STAGE_COMPLETED,
)

VALID_STATUSES = (
    STATUS_ACTIVE,
    STATUS_PAUSED,
    STATUS_COMPLETED,
)

VALID_LEVELS = ("beginner", "intermediate", "advanced")
VALID_LANGUAGES = ("english", "hindi", "hinglish")


class TutorSession(Base):
    """Personalized conversational tutoring session focused on mastering a topic."""

    __tablename__ = "tutor_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'PAUSED', 'COMPLETED', 'active', 'paused', 'completed')",
            name="valid_tutor_session_status",
        ),
        CheckConstraint(
            "current_stage IN ('DIAGNOSIS', 'EXPLANATION', 'EXAMPLE', 'PRACTICE', 'VERIFICATION', 'COMPLETED')",
            name="valid_tutor_session_stage",
        ),
        CheckConstraint(
            "explanation_level IN ('beginner', 'intermediate', 'advanced')",
            name="valid_explanation_level",
        ),
        CheckConstraint(
            "language IN ('english', 'hindi', 'hinglish')",
            name="valid_tutor_language",
        ),
        Index("ix_tutor_sessions_user_course", "user_id", "course_id"),
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
    plan_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("plan_items.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    language: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="english",
        server_default="english",
        index=True,
    )
    explanation_level: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="intermediate",
        server_default="intermediate",
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=STATUS_ACTIVE,
        server_default=STATUS_ACTIVE,
        index=True,
    )
    current_stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=STAGE_DIAGNOSIS,
        server_default=STAGE_DIAGNOSIS,
        index=True,
    )
    session_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.current_timestamp(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        server_default=func.current_timestamp(),
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="tutor_sessions")
    course: Mapped[Course] = relationship("Course", back_populates="tutor_sessions")
    topic: Mapped[Topic] = relationship("Topic", back_populates="tutor_sessions")
    plan_item: Mapped[Optional[PlanItem]] = relationship("PlanItem")
    messages: Mapped[List[TutorMessage]] = relationship(
        "TutorMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="TutorMessage.created_at",
    )
    attempts: Mapped[List[Attempt]] = relationship(
        "Attempt",
        back_populates="tutor_session",
    )

    def __repr__(self) -> str:
        return (
            f"<TutorSession id={self.id} user_id={self.user_id} "
            f"topic_id={self.topic_id} stage={self.current_stage} status={self.status}>"
        )
