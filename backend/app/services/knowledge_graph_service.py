"""Knowledge graph service for generating, validating, and traversing course topic DAGs."""
from __future__ import annotations

import logging
from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.topic import Topic
from app.models.topic_prerequisite import TopicPrerequisite
from app.schemas.topic import (
    TopicGraphData,
    TopicGraphEdge,
    TopicGraphNode,
    TopicGraphResponse,
)
from app.services.topic_validation_service import detect_prerequisite_cycles

logger = logging.getLogger(__name__)


class KnowledgeGraphError(Exception):
    """Base exception for knowledge graph generation errors."""


class TopicNotFoundError(KnowledgeGraphError):
    """Raised when a requested topic is not found."""


class CourseOwnershipError(KnowledgeGraphError):
    """Raised when course does not belong to the user."""


def build_topic_graph(
    topics: list[Topic],
    prerequisites: list[TopicPrerequisite],
) -> TopicGraphData:
    """Build directed graph representation from topics and prerequisite records.

    Edge direction: `Prerequisite (source) -> Dependent Topic (target)`.
    Example: `Recursion -> Dynamic Programming`.
    """
    topic_map = {str(t.id): t for t in topics}

    nodes: list[TopicGraphNode] = []
    for t in topics:
        sub_count = len(t.subtopics) if hasattr(t, "subtopics") and t.subtopics else 0
        nodes.append(
            TopicGraphNode(
                id=str(t.id),
                label=t.name,
                unit=t.unit_name,
                difficulty=t.difficulty,
                source_type=t.source_type,
                description=t.description,
                parent_id=str(t.parent_id) if t.parent_id else None,
                subtopic_count=sub_count,
            )
        )

    edges: list[TopicGraphEdge] = []
    edge_pairs: list[tuple[str, str]] = []

    for p in prerequisites:
        s_id = str(p.prerequisite_id)
        t_id = str(p.topic_id)

        # Both endpoints must be among the course's topics
        if s_id in topic_map and t_id in topic_map:
            edges.append(
                TopicGraphEdge(
                    source=s_id,
                    target=t_id,
                    relationship="prerequisite",
                    confidence=p.confidence,
                    reason=p.reason,
                )
            )
            edge_pairs.append((s_id, t_id))

    is_dag = not detect_prerequisite_cycles(edge_pairs)

    return TopicGraphData(
        nodes=nodes,
        edges=edges,
        total_nodes=len(nodes),
        total_edges=len(edges),
        is_dag=is_dag,
    )


def validate_graph(graph_data: TopicGraphData) -> bool:
    """Validate that the graph is an acyclic directed graph (DAG)."""
    edges = [(e.source, e.target) for e in graph_data.edges]
    return not detect_prerequisite_cycles(edges)


def get_course_topic_graph(
    db: Session,
    course_id: uuid.UUID,
    user_id: uuid.UUID,
) -> TopicGraphResponse:
    """Retrieve full topic knowledge graph for a course verified by user ownership."""
    course = db.scalar(
        select(Course).where(Course.id == course_id, Course.user_id == user_id)
    )
    if not course:
        raise CourseOwnershipError("Course not found or access denied")

    # Fetch root topics for the graph (or all topics including subtopics)
    # Including root topics keeps the high-level concept graph clear and clean
    topics = db.scalars(
        select(Topic)
        .where(Topic.course_id == course_id, Topic.parent_id.is_(None))
        .order_by(Topic.unit_name.nulls_last(), Topic.name)
    ).all()

    topic_ids = [t.id for t in topics]
    if not topic_ids:
        empty_data = TopicGraphData(nodes=[], edges=[], total_nodes=0, total_edges=0, is_dag=True)
        return TopicGraphResponse(success=True, data=empty_data, message="No topics found for course")

    prerequisites = db.scalars(
        select(TopicPrerequisite).where(
            TopicPrerequisite.topic_id.in_(topic_ids),
            TopicPrerequisite.prerequisite_id.in_(topic_ids),
        )
    ).all()

    graph_data = build_topic_graph(list(topics), list(prerequisites))
    return TopicGraphResponse(
        success=True,
        data=graph_data,
        message="Topic knowledge graph retrieved successfully",
    )


def get_topic_prerequisites(
    db: Session,
    topic_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[TopicPrerequisite]:
    """Get all incoming prerequisite links for a specific topic (prerequisites required to learn it)."""
    topic = db.scalar(select(Topic).where(Topic.id == topic_id))
    if not topic:
        raise TopicNotFoundError(f"Topic {topic_id} not found")

    course = db.scalar(
        select(Course).where(Course.id == topic.course_id, Course.user_id == user_id)
    )
    if not course:
        raise CourseOwnershipError("Access denied for this topic's course")

    return list(topic.prerequisite_links)


def get_dependent_topics(
    db: Session,
    topic_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[TopicPrerequisite]:
    """Get all outgoing prerequisite links where this topic is a prerequisite for another topic."""
    topic = db.scalar(select(Topic).where(Topic.id == topic_id))
    if not topic:
        raise TopicNotFoundError(f"Topic {topic_id} not found")

    course = db.scalar(
        select(Course).where(Course.id == topic.course_id, Course.user_id == user_id)
    )
    if not course:
        raise CourseOwnershipError("Access denied for this topic's course")

    return list(topic.dependent_links)

