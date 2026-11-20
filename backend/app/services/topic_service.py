"""Service for managing course topic queries, unit groupings, updates, and deletions."""
from __future__ import annotations

from collections import defaultdict
import logging
from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.course import Course
from app.models.topic import Topic
from app.models.topic_prerequisite import TopicPrerequisite
from app.schemas.topic import (
    CourseTopicsData,
    CourseTopicsResponse,
    DependentLinkInfo,
    PrerequisiteLinkInfo,
    SubtopicResponse,
    TopicDetailResponse,
    TopicResponse,
    TopicUpdate,
    UnitGroup,
)
from app.services.topic_validation_service import normalize_difficulty, normalize_topic_name

logger = logging.getLogger(__name__)


class TopicServiceError(Exception):
    """Base exception for topic service operations."""


class TopicNotFoundError(TopicServiceError):
    """Raised when topic is missing or not owned by user."""


class TopicValidationError(TopicServiceError):
    """Raised when an update contains invalid topic parameters."""


def get_course_topics_grouped_by_unit(
    db: Session,
    course_id: uuid.UUID,
    user_id: uuid.UUID,
) -> CourseTopicsResponse:
    """Retrieve all topics for a course grouped by unit with hierarchical subtopics."""
    course = db.scalar(
        select(Course).where(Course.id == course_id, Course.user_id == user_id)
    )
    if not course:
        raise TopicNotFoundError("Course not found or access denied")

    # Fetch root topics with their subtopics eagerly loaded
    root_topics = db.scalars(
        select(Topic)
        .where(Topic.course_id == course_id, Topic.parent_id.is_(None))
        .options(selectinload(Topic.subtopics))
        .order_by(Topic.unit_name.nulls_last(), Topic.name)
    ).all()

    unit_groups_dict: dict[str, list[TopicResponse]] = defaultdict(list)
    total_subtopics = 0

    for t in root_topics:
        subs = [
            SubtopicResponse(
                id=s.id,
                name=s.name,
                description=s.description,
                difficulty=s.difficulty,
                parent_id=s.parent_id,
            )
            for s in t.subtopics
        ]
        total_subtopics += len(subs)

        resp = TopicResponse(
            id=t.id,
            course_id=t.course_id,
            name=t.name,
            description=t.description,
            difficulty=t.difficulty,
            parent_id=t.parent_id,
            unit_name=t.unit_name,
            source_type=t.source_type,
            source_pages=t.source_pages if isinstance(t.source_pages, list) else None,
            created_at=t.created_at,
            subtopics=subs,
        )
        group_key = t.unit_name or "Unassigned Unit"
        unit_groups_dict[group_key].append(resp)

    unit_groups = [
        UnitGroup(unit_name=k, topics=v) for k, v in unit_groups_dict.items()
    ]

    data = CourseTopicsData(
        units=unit_groups,
        total_units=len(unit_groups),
        total_topics=len(root_topics),
        total_subtopics=total_subtopics,
    )

    return CourseTopicsResponse(
        success=True,
        data=data,
        message="Topics retrieved successfully",
    )


def get_topic_by_id(
    db: Session,
    topic_id: uuid.UUID,
    user_id: uuid.UUID,
) -> TopicDetailResponse:
    """Get topic details including subtopics, prerequisites, and dependent topics."""
    topic = db.scalar(
        select(Topic)
        .where(Topic.id == topic_id)
        .options(
            selectinload(Topic.subtopics),
            selectinload(Topic.prerequisite_links).selectinload(TopicPrerequisite.prerequisite),
            selectinload(Topic.dependent_links).selectinload(TopicPrerequisite.topic),
            selectinload(Topic.course),
        )
    )
    if not topic or topic.course.user_id != user_id:
        raise TopicNotFoundError(f"Topic {topic_id} not found")

    subs = [
        SubtopicResponse(
            id=s.id,
            name=s.name,
            description=s.description,
            difficulty=s.difficulty,
            parent_id=s.parent_id,
        )
        for s in topic.subtopics
    ]

    prereqs = [
        PrerequisiteLinkInfo(
            id=link.prerequisite.id,
            name=link.prerequisite.name,
            confidence=link.confidence,
            reason=link.reason,
        )
        for link in topic.prerequisite_links
        if link.prerequisite is not None
    ]

    dependents = [
        DependentLinkInfo(
            id=link.topic.id,
            name=link.topic.name,
            confidence=link.confidence,
            reason=link.reason,
        )
        for link in topic.dependent_links
        if link.topic is not None
    ]

    return TopicDetailResponse(
        id=topic.id,
        course_id=topic.course_id,
        name=topic.name,
        description=topic.description,
        difficulty=topic.difficulty,
        parent_id=topic.parent_id,
        unit_name=topic.unit_name,
        source_type=topic.source_type,
        source_pages=topic.source_pages if isinstance(topic.source_pages, list) else None,
        created_at=topic.created_at,
        subtopics=subs,
        prerequisites=prereqs,
        dependents=dependents,
    )


def update_topic(
    db: Session,
    topic_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: TopicUpdate,
) -> TopicDetailResponse:
    """Update topic fields (name, description, difficulty, unit_name)."""
    topic = db.scalar(
        select(Topic)
        .where(Topic.id == topic_id)
        .options(selectinload(Topic.course))
    )
    if not topic or topic.course.user_id != user_id:
        raise TopicNotFoundError(f"Topic {topic_id} not found")

    data = payload.model_dump(exclude_unset=True)

    if "name" in data and data["name"] is not None:
        clean_name = normalize_topic_name(data["name"])
        if not clean_name:
            raise TopicValidationError("Topic name cannot be blank")

        # Check for duplicate sibling topic
        existing = db.scalar(
            select(Topic).where(
                Topic.course_id == topic.course_id,
                Topic.name == clean_name,
                Topic.parent_id == topic.parent_id,
                Topic.id != topic.id,
            )
        )
        if existing:
            raise TopicValidationError(f"A topic named '{clean_name}' already exists in this course.")
        topic.name = clean_name

    if "description" in data:
        topic.description = (data["description"] or "").strip() or None

    if "difficulty" in data and data["difficulty"] is not None:
        topic.difficulty = normalize_difficulty(data["difficulty"])

    if "unit_name" in data:
        topic.unit_name = (data["unit_name"] or "").strip() or None

    db.flush()
    db.commit()
    return get_topic_by_id(db, topic_id, user_id)


def delete_topic(
    db: Session,
    topic_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Delete a topic and cleanly cascade its child subtopics and prerequisite links."""
    topic = db.scalar(
        select(Topic)
        .where(Topic.id == topic_id)
        .options(selectinload(Topic.course))
    )
    if not topic or topic.course.user_id != user_id:
        raise TopicNotFoundError(f"Topic {topic_id} not found")

    db.delete(topic)
    db.commit()

