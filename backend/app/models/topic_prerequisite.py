from __future__ import annotations

from collections import defaultdict, deque
from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, Uuid, event, select
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.topic import Topic


class CircularPrerequisiteError(ValueError):
    """Raised when adding topic prerequisite edges would create a cycle."""


class TopicPrerequisite(Base):
    """Directed prerequisite edge: `topic_id` requires `prerequisite_id` first."""

    __tablename__ = "topic_prerequisites"
    __table_args__ = (
        CheckConstraint(
            "topic_id <> prerequisite_id",
            name="no_self_prerequisite",
        ),
        Index("ix_topic_prerequisites_prerequisite_id", "prerequisite_id"),
    )

    topic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        primary_key=True,
    )
    prerequisite_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Relationships
    topic: Mapped[Topic] = relationship(
        "Topic",
        foreign_keys=[topic_id],
        back_populates="prerequisite_links",
    )
    prerequisite: Mapped[Topic] = relationship(
        "Topic",
        foreign_keys=[prerequisite_id],
        back_populates="dependent_links",
    )

    def __repr__(self) -> str:
        return (
            f"<TopicPrerequisite topic_id={self.topic_id} "
            f"prerequisite_id={self.prerequisite_id}>"
        )


def _edge_keys(link: TopicPrerequisite) -> tuple[Any, Any]:
    """Resolve comparable node keys even if related Topic instances are not yet flushed."""
    t_key: Any = link.topic_id
    if t_key is None and link.topic is not None:
        t_key = link.topic.id if link.topic.id is not None else ("obj", id(link.topic))

    p_key: Any = link.prerequisite_id
    if p_key is None and link.prerequisite is not None:
        p_key = (
            link.prerequisite.id
            if link.prerequisite.id is not None
            else ("obj", id(link.prerequisite))
        )

    return t_key, p_key


def _has_path(adjacency: dict[Any, set[Any]], start: Any, target: Any) -> bool:
    """Return True if `target` is reachable from `start` in the prerequisite DAG."""
    visited: set[Any] = set()
    queue: deque[Any] = deque([start])
    while queue:
        current = queue.popleft()
        if current == target:
            return True
        if current in visited:
            continue
        visited.add(current)
        for neighbor in adjacency.get(current, ()):
            if neighbor not in visited:
                queue.append(neighbor)
    return False


def validate_no_prerequisite_cycle(
    session: Session,
    topic_id: uuid.UUID,
    prerequisite_id: uuid.UUID,
) -> None:
    """Explicitly validate that adding `(topic_id -> prerequisite_id)` keeps the graph acyclic."""
    if topic_id == prerequisite_id:
        raise CircularPrerequisiteError(
            f"Topic {topic_id} cannot be a prerequisite of itself."
        )

    with session.no_autoflush:
        existing_rows = session.execute(
            select(TopicPrerequisite.topic_id, TopicPrerequisite.prerequisite_id)
        ).all()

    adjacency: dict[Any, set[Any]] = defaultdict(set)
    for t_id, p_id in existing_rows:
        adjacency[t_id].add(p_id)

    if _has_path(adjacency, prerequisite_id, topic_id):
        raise CircularPrerequisiteError(
            f"Circular prerequisite detected: topic {topic_id} is already an ancestor "
            f"prerequisite of {prerequisite_id}."
        )


@event.listens_for(Session, "before_flush")
def _prevent_circular_prerequisites(
    session: Session,
    flush_context: Any,
    instances: Any,
) -> None:
    """Guard against circular prerequisite graphs whenever TopicPrerequisite rows are flushed."""
    pending_links = [
        obj
        for obj in list(session.new) + list(session.dirty)
        if isinstance(obj, TopicPrerequisite)
    ]
    if not pending_links:
        return

    # Only evaluate non-self edges here; self-loops (topic_id == prerequisite_id) are
    # enforced at the database level via the CHECK constraint.
    candidate_edges: list[tuple[Any, Any]] = []
    for link in pending_links:
        t_key, p_key = _edge_keys(link)
        if t_key is not None and p_key is not None and t_key != p_key:
            candidate_edges.append((t_key, p_key))

    if not candidate_edges:
        return

    deleted_edges = {
        _edge_keys(obj)
        for obj in session.deleted
        if isinstance(obj, TopicPrerequisite)
    }

    with session.no_autoflush:
        existing_rows = session.execute(
            select(TopicPrerequisite.topic_id, TopicPrerequisite.prerequisite_id)
        ).all()

    adjacency: dict[Any, set[Any]] = defaultdict(set)
    for t_id, p_id in existing_rows:
        if (t_id, p_id) not in deleted_edges:
            adjacency[t_id].add(p_id)

    # Add candidate edges incrementally and verify no cycle is introduced
    for t_key, p_key in candidate_edges:
        if _has_path(adjacency, p_key, t_key):
            raise CircularPrerequisiteError(
                f"Circular prerequisite detected when linking topic {t_key} -> "
                f"prerequisite {p_key}."
            )
        adjacency[t_key].add(p_key)

