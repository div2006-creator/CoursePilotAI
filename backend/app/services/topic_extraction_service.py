"""Service for extracting academic topics and prerequisite relationships using local LLM inference."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.llm import (
    LLMError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
    generate_completion,
)
from app.models.course import Course
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.topic import Topic
from app.models.topic_prerequisite import TopicPrerequisite
from app.schemas.topic import TopicExtractionData, TopicExtractionResponse
from app.services.topic_validation_service import (
    TopicValidationError,
    ValidatedTopicExtractionResult,
    validate_extracted_topics,
)

logger = logging.getLogger(__name__)

PROMPT_FILE_PATH = (
    Path(__file__).resolve().parents[1] / "agents" / "prompts" / "topic_extraction_prompt.txt"
)


class TopicExtractionError(Exception):
    """Base exception for topic extraction failures."""


class NoCompletedDocumentsError(TopicExtractionError):
    """Raised when no completed documents exist for the course."""


class CourseAccessDeniedError(TopicExtractionError):
    """Raised when the course is not found or not owned by user."""


def load_extraction_prompt() -> str:
    """Load the academic syllabus analyzer prompt from disk."""
    if not PROMPT_FILE_PATH.exists():
        logger.warning("Prompt file not found at %s; using embedded fallback.", PROMPT_FILE_PATH)
        return (
            "You are an academic syllabus analyzer. Extract topics, units, subtopics, "
            "and prerequisite dependencies in valid JSON format."
        )
    return PROMPT_FILE_PATH.read_text(encoding="utf-8")


def prepare_course_syllabus_text(
    documents: list[Document],
    max_total_chars: int = 40000,
) -> str:
    """Combine and format document chunks into a structured text prompt for the LLM."""
    sections: list[str] = []
    total_chars = 0

    for doc in documents:
        doc_header = f"=== DOCUMENT: {doc.filename} ==="
        sections.append(doc_header)
        total_chars += len(doc_header)

        # Iterate chunks ordered by chunk_index
        sorted_chunks = sorted(doc.chunks, key=lambda c: c.chunk_index)
        for chunk in sorted_chunks:
            page_info = f"[Page {chunk.page_number}] " if chunk.page_number else ""
            chunk_text = f"{page_info}{chunk.content.strip()}"
            if total_chars + len(chunk_text) > max_total_chars:
                logger.info(
                    "Truncating document chunks at %d characters to stay within LLM context limit.",
                    max_total_chars,
                )
                break
            sections.append(chunk_text)
            total_chars += len(chunk_text)

    return "\n\n".join(sections)


def extract_topics_from_course(
    db: Session,
    course_id: uuid.UUID,
    user_id: uuid.UUID,
    llm_generator=generate_completion,
) -> TopicExtractionResponse:
    """Run AI topic extraction on uploaded documents for a course and persist topics and prerequisites."""
    course = db.scalar(
        select(Course).where(Course.id == course_id, Course.user_id == user_id)
    )
    if not course:
        raise CourseAccessDeniedError("Course not found or access denied")

    # Retrieve all completed documents for this course
    documents = db.scalars(
        select(Document)
        .where(
            Document.course_id == course_id,
            Document.status.in_(["completed", "processed"]),
        )
        .options(selectinload(Document.chunks))
    ).all()

    if not documents:
        raise NoCompletedDocumentsError(
            "No completed documents found for this course. Please upload a course syllabus first."
        )

    # Assemble document chunks into syllabus content
    syllabus_text = prepare_course_syllabus_text(list(documents))
    if not syllabus_text.strip():
        raise NoCompletedDocumentsError(
            "Uploaded documents contain no extractable text chunks."
        )

    system_prompt = load_extraction_prompt()
    user_prompt = (
        f"Below is the complete extracted syllabus text for the course '{course.title}':\n\n"
        f"{syllabus_text}\n\n"
        "Extract the topics, units, subtopics, and prerequisite relationships in strict JSON format."
    )

    try:
        raw_response = llm_generator(
            prompt=user_prompt,
            system=system_prompt,
            response_format="json",
        )
    except (OllamaConnectionError, OllamaModelNotFoundError, OllamaTimeoutError, LLMError) as exc:
        logger.error("LLM generation failed during topic extraction: %s", exc)
        raise TopicExtractionError(str(exc)) from exc

    try:
        validated_result: ValidatedTopicExtractionResult = validate_extracted_topics(raw_response)
    except TopicValidationError as exc:
        logger.error("Failed to validate extracted topics: %s", exc)
        raise TopicExtractionError(f"AI extraction output validation failed: {exc}") from exc

    if not validated_result.topics:
        raise TopicExtractionError("No valid topics could be extracted from the provided syllabus.")

    # Persist topics and prerequisites idempotently in a database transaction
    topics_created = 0
    subtopics_created = 0
    prerequisites_created = 0
    created_topic_names: list[str] = []

    try:
        # Load existing topics for this course to avoid duplicate insertion
        existing_topics_query = db.scalars(
            select(Topic)
            .where(Topic.course_id == course_id)
            .options(selectinload(Topic.subtopics))
        ).all()

        # Map by (name.lower(), parent_id)
        topic_registry: dict[tuple[str, Optional[uuid.UUID]], Topic] = {
            (t.name.lower(), t.parent_id): t for t in existing_topics_query
        }

        # 1. Save or update root topics
        root_map: dict[str, Topic] = {}
        for vt in validated_result.topics:
            key = (vt.name.lower(), None)
            if key in topic_registry:
                topic_record = topic_registry[key]
                # Update metadata
                if vt.description and not topic_record.description:
                    topic_record.description = vt.description
                topic_record.difficulty = vt.difficulty
                topic_record.unit_name = vt.unit_name or topic_record.unit_name
                topic_record.source_type = vt.source_type
                if vt.source_pages:
                    topic_record.source_pages = vt.source_pages
            else:
                topic_record = Topic(
                    course_id=course_id,
                    name=vt.name,
                    description=vt.description,
                    difficulty=vt.difficulty,
                    parent_id=None,
                    unit_name=vt.unit_name,
                    source_type=vt.source_type,
                    source_pages=vt.source_pages,
                )
                db.add(topic_record)
                db.flush()
                topic_registry[key] = topic_record
                topics_created += 1

            root_map[vt.name.lower()] = topic_record
            created_topic_names.append(topic_record.name)

            # 2. Save or update subtopics
            for sub in vt.subtopics:
                sub_key = (sub.name.lower(), topic_record.id)
                if sub_key not in topic_registry:
                    sub_record = Topic(
                        course_id=course_id,
                        name=sub.name,
                        description=sub.description,
                        difficulty=vt.difficulty,
                        parent_id=topic_record.id,
                        unit_name=vt.unit_name,
                        source_type=vt.source_type,
                        source_pages=vt.source_pages,
                    )
                    db.add(sub_record)
                    db.flush()
                    topic_registry[sub_key] = sub_record
                    subtopics_created += 1

        # 3. Save prerequisite links
        # Direction: prerequisite -> topic (topic requires prerequisite)
        for vp in validated_result.prerequisites:
            topic_obj = root_map.get(vp.topic_name.lower())
            prereq_obj = root_map.get(vp.prerequisite_name.lower())

            if not topic_obj or not prereq_obj:
                continue

            # Check if this link already exists
            existing_link = db.scalar(
                select(TopicPrerequisite).where(
                    TopicPrerequisite.topic_id == topic_obj.id,
                    TopicPrerequisite.prerequisite_id == prereq_obj.id,
                )
            )
            if not existing_link:
                new_link = TopicPrerequisite(
                    topic_id=topic_obj.id,
                    prerequisite_id=prereq_obj.id,
                    confidence=vp.confidence,
                    reason=vp.reason,
                )
                db.add(new_link)
                prerequisites_created += 1

        db.commit()

    except Exception as exc:
        db.rollback()
        logger.error("Database transaction rolled back during topic extraction: %s", exc)
        raise TopicExtractionError(f"Database error while saving topics: {exc}") from exc

    return TopicExtractionResponse(
        success=True,
        data=TopicExtractionData(
            course_id=str(course_id),
            units_extracted=len(validated_result.units),
            topics_created=topics_created,
            subtopics_created=subtopics_created,
            prerequisites_created=prerequisites_created,
            sample_topics=created_topic_names[:5],
        ),
        message="Topic extraction and knowledge graph completed successfully",
    )

