from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.attempt import Attempt
    from app.models.course import Course
    from app.models.plan_item import PlanItem
    from app.models.question import Question
    from app.models.topic_mastery import TopicMastery
    from app.models.topic_prerequisite import TopicPrerequisite


class Topic(Base):
    """Academic concept or module within a course syllabus."""

    __tablename__ = "topics"
    __table_args__ = (
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="no_self_parent"),
        Index("ix_topics_course_name", "course_id", "name"),
        Index("ix_topics_course_difficulty", "course_id", "difficulty"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="beginner",
        server_default="beginner",
        index=True,
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("topics.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    # Relationships
    course: Mapped[Course] = relationship("Course", back_populates="topics")
    parent: Mapped[Optional[Topic]] = relationship(
        "Topic",
        remote_side="Topic.id",
        back_populates="subtopics",
    )
    subtopics: Mapped[list[Topic]] = relationship(
        "Topic",
        back_populates="parent",
    )

    # Prerequisite graph association objects
    prerequisite_links: Mapped[list[TopicPrerequisite]] = relationship(
        "TopicPrerequisite",
        foreign_keys="TopicPrerequisite.topic_id",
        back_populates="topic",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    dependent_links: Mapped[list[TopicPrerequisite]] = relationship(
        "TopicPrerequisite",
        foreign_keys="TopicPrerequisite.prerequisite_id",
        back_populates="prerequisite",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Direct read-only convenience views for graph traversal
    prerequisites: Mapped[list[Topic]] = relationship(
        "Topic",
        secondary="topic_prerequisites",
        primaryjoin="Topic.id == TopicPrerequisite.topic_id",
        secondaryjoin="Topic.id == TopicPrerequisite.prerequisite_id",
        viewonly=True,
    )
    dependents: Mapped[list[Topic]] = relationship(
        "Topic",
        secondary="topic_prerequisites",
        primaryjoin="Topic.id == TopicPrerequisite.prerequisite_id",
        secondaryjoin="Topic.id == TopicPrerequisite.topic_id",
        viewonly=True,
    )

    questions: Mapped[list[Question]] = relationship(
        "Question",
        back_populates="topic",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    attempts: Mapped[list[Attempt]] = relationship(
        "Attempt",
        back_populates="topic",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    masteries: Mapped[list[TopicMastery]] = relationship(
        "TopicMastery",
        back_populates="topic",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    plan_items: Mapped[list[PlanItem]] = relationship(
        "PlanItem",
        back_populates="topic",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Topic id={self.id} name={self.name!r}>"

