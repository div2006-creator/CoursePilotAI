from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional
import uuid

from sqlalchemy import ForeignKey, Index, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.attempt import Attempt
    from app.models.topic import Topic


class Question(Base):
    """Diagnostic or practice question linked to a course topic."""

    __tablename__ = "questions"
    __table_args__ = (
        Index("ix_questions_topic_difficulty", "topic_id", "difficulty"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[Any] = mapped_column(JSONB, nullable=False)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="medium",
        server_default="medium",
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="seed",
        server_default="seed",
        index=True,
    )

    # Relationships
    topic: Mapped[Topic] = relationship("Topic", back_populates="questions")
    attempts: Mapped[list[Attempt]] = relationship(
        "Attempt",
        back_populates="question",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Question id={self.id} topic_id={self.topic_id} difficulty={self.difficulty!r}>"

