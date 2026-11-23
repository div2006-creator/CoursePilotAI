"""TutorMessage ORM model for Part 10: Personalized AI Tutor."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utc_now

if TYPE_CHECKING:
    from app.models.topic import Topic
    from app.models.tutor_session import TutorSession

ROLE_USER = "USER"
ROLE_ASSISTANT = "ASSISTANT"
ROLE_SYSTEM = "SYSTEM"

MSG_TYPE_CHAT = "chat"
MSG_TYPE_EXPLANATION = "explanation"
MSG_TYPE_QUESTION = "question"
MSG_TYPE_HINT = "hint"
MSG_TYPE_FEEDBACK = "feedback"
MSG_TYPE_SOURCE = "source_reference"


class TutorMessage(Base):
    """Individual dialogue turn in an AI tutoring session."""

    __tablename__ = "tutor_messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('USER', 'ASSISTANT', 'SYSTEM', 'user', 'assistant', 'system')",
            name="valid_tutor_message_role",
        ),
        Index("ix_tutor_messages_session_created", "session_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tutor_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    message_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=MSG_TYPE_CHAT,
        server_default=MSG_TYPE_CHAT,
        index=True,
    )
    related_topic_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("topics.id", ondelete="SET NULL"),
        nullable=True,
    )
    sources: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.current_timestamp(),
        nullable=False,
        index=True,
    )

    # Relationships
    session: Mapped[TutorSession] = relationship("TutorSession", back_populates="messages")
    topic: Mapped[Optional[Topic]] = relationship("Topic")

    def __repr__(self) -> str:
        return (
            f"<TutorMessage id={self.id} session_id={self.session_id} "
            f"role={self.role} type={self.message_type}>"
        )

