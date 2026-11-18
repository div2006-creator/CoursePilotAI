from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utc_now

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.plan_item import PlanItem
    from app.models.user import User


class StudyPlan(Base):
    """Versioned personalized study plan generated for a learner and course."""

    __tablename__ = "study_plans"
    __table_args__ = (
        CheckConstraint("version >= 1", name="version_positive"),
        Index("ix_study_plans_user_course_status", "user_id", "course_id", "status"),
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
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",
        server_default="active",
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.current_timestamp(),
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="study_plans")
    course: Mapped[Course] = relationship("Course", back_populates="study_plans")
    items: Mapped[list[PlanItem]] = relationship(
        "PlanItem",
        back_populates="plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"<StudyPlan id={self.id} course_id={self.course_id} "
            f"version={self.version} status={self.status!r}>"
        )
