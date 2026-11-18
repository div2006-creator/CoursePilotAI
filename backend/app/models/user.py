from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utc_now

if TYPE_CHECKING:
    from app.models.agent_run import AgentRun
    from app.models.attempt import Attempt
    from app.models.course import Course
    from app.models.study_plan import StudyPlan
    from app.models.topic_mastery import TopicMastery


class User(Base):
    """Registered learner account."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.current_timestamp(),
        nullable=False,
    )

    # Relationships
    courses: Mapped[list[Course]] = relationship(
        "Course",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    attempts: Mapped[list[Attempt]] = relationship(
        "Attempt",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    topic_masteries: Mapped[list[TopicMastery]] = relationship(
        "TopicMastery",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    study_plans: Mapped[list[StudyPlan]] = relationship(
        "StudyPlan",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    agent_runs: Mapped[list[AgentRun]] = relationship(
        "AgentRun",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
