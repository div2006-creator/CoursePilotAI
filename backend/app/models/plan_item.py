from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.study_plan import StudyPlan
    from app.models.topic import Topic


class PlanItem(Base):
    """Scheduled topic study session belonging to a StudyPlan."""

    __tablename__ = "plan_items"
    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="duration_minutes_positive"),
        CheckConstraint("priority >= 1", name="priority_positive"),
        Index("ix_plan_items_plan_date", "plan_id", "scheduled_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("study_plans.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )

    # Relationships
    plan: Mapped[StudyPlan] = relationship("StudyPlan", back_populates="items")
    topic: Mapped[Topic] = relationship("Topic", back_populates="plan_items")

    def __repr__(self) -> str:
        return (
            f"<PlanItem id={self.id} plan_id={self.plan_id} "
            f"topic_id={self.topic_id} date={self.scheduled_date}>"
        )

