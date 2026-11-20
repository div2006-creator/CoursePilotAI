"""API routes for Topic Extraction, Topic CRUD, and Knowledge Graph representations."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.topic import (
    CourseTopicsResponse,
    TopicDetailResponse,
    TopicExtractionResponse,
    TopicGraphResponse,
    TopicSingleResponse,
    TopicUpdate,
)
from app.services.knowledge_graph_service import (
    CourseOwnershipError,
    get_course_topic_graph,
)
from app.services.topic_extraction_service import (
    CourseAccessDeniedError,
    NoCompletedDocumentsError,
    TopicExtractionError,
    extract_topics_from_course,
)
from app.services.topic_service import (
    TopicNotFoundError,
    TopicValidationError,
    delete_topic,
    get_course_topics_grouped_by_unit,
    get_topic_by_id,
    update_topic,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Course-scoped Topic & Graph Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/courses/{course_id}/extract-topics",
    response_model=TopicExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract topics and prerequisite knowledge graph from course documents",
)
def extract_course_topics_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TopicExtractionResponse:
    """Analyze course syllabus documents with local LLM and generate a topic knowledge graph."""
    try:
        return extract_topics_from_course(db, course_id, current_user.id)
    except CourseAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except NoCompletedDocumentsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except TopicExtractionError as exc:
        err_msg = str(exc)
        status_code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if "connect to Ollama" in err_msg or "not found on Ollama" in err_msg
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        raise HTTPException(
            status_code=status_code,
            detail=err_msg,
        ) from exc


@router.get(
    "/courses/{course_id}/topics",
    response_model=CourseTopicsResponse,
    status_code=status.HTTP_200_OK,
    summary="List all topics for a course grouped by unit",
)
def list_course_topics_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CourseTopicsResponse:
    try:
        return get_course_topics_grouped_by_unit(db, course_id, current_user.id)
    except TopicNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/courses/{course_id}/topic-graph",
    response_model=TopicGraphResponse,
    status_code=status.HTTP_200_OK,
    summary="Get knowledge graph nodes and directed prerequisite edges for visualization",
)
def get_course_topic_graph_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TopicGraphResponse:
    try:
        return get_course_topic_graph(db, course_id, current_user.id)
    except CourseOwnershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# Individual Topic Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/topics/{topic_id}",
    response_model=TopicSingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get individual topic details with subtopics and prerequisites",
)
def get_topic_endpoint(
    topic_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TopicSingleResponse:
    try:
        detail = get_topic_by_id(db, topic_id, current_user.id)
    except TopicNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return TopicSingleResponse(
        success=True,
        data=detail,
        message="Topic retrieved successfully",
    )


@router.patch(
    "/topics/{topic_id}",
    response_model=TopicSingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update topic title, description, difficulty, or unit name",
)
def update_topic_endpoint(
    topic_id: uuid.UUID,
    payload: TopicUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TopicSingleResponse:
    try:
        updated = update_topic(db, topic_id, current_user.id, payload)
    except TopicNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except TopicValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return TopicSingleResponse(
        success=True,
        data=updated,
        message="Topic updated successfully",
    )


@router.delete(
    "/topics/{topic_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a topic and clean up associated prerequisite links",
)
def delete_topic_endpoint(
    topic_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    try:
        delete_topic(db, topic_id, current_user.id)
    except TopicNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)

