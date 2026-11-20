"""Pydantic schemas for Topic Extraction, Topic CRUD, and Knowledge Graph representations."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class SubtopicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str] = None
    difficulty: str
    parent_id: Optional[uuid.UUID] = None


class PrerequisiteLinkInfo(BaseModel):
    id: uuid.UUID
    name: str
    confidence: float
    reason: Optional[str] = None


class DependentLinkInfo(BaseModel):
    id: uuid.UUID
    name: str
    confidence: float
    reason: Optional[str] = None


class TopicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    name: str
    description: Optional[str] = None
    difficulty: str
    parent_id: Optional[uuid.UUID] = None
    unit_name: Optional[str] = None
    source_type: str
    source_pages: Optional[list[int]] = None
    created_at: datetime
    subtopics: list[SubtopicResponse] = Field(default_factory=list)


class TopicDetailResponse(TopicResponse):
    prerequisites: list[PrerequisiteLinkInfo] = Field(default_factory=list)
    dependents: list[DependentLinkInfo] = Field(default_factory=list)


class UnitGroup(BaseModel):
    unit_name: str
    topics: list[TopicResponse] = Field(default_factory=list)


class CourseTopicsData(BaseModel):
    units: list[UnitGroup] = Field(default_factory=list)
    total_units: int
    total_topics: int
    total_subtopics: int


class CourseTopicsResponse(BaseModel):
    success: bool = True
    data: CourseTopicsData
    message: str = "Topics retrieved successfully"


class TopicSingleResponse(BaseModel):
    success: bool = True
    data: TopicDetailResponse
    message: str = "Topic retrieved successfully"


class TopicUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    difficulty: Optional[str] = Field(default=None, max_length=50)
    unit_name: Optional[str] = Field(default=None, max_length=100)


class TopicGraphNode(BaseModel):
    id: str
    label: str
    unit: Optional[str] = None
    difficulty: str = "medium"
    source_type: str = "explicit"
    description: Optional[str] = None
    parent_id: Optional[str] = None
    subtopic_count: int = 0


class TopicGraphEdge(BaseModel):
    source: str  # Prerequisite topic id
    target: str  # Dependent topic id
    relationship: str = "prerequisite"
    confidence: float = 1.0
    reason: Optional[str] = None


class TopicGraphData(BaseModel):
    nodes: list[TopicGraphNode] = Field(default_factory=list)
    edges: list[TopicGraphEdge] = Field(default_factory=list)
    total_nodes: int = 0
    total_edges: int = 0
    is_dag: bool = True


class TopicGraphResponse(BaseModel):
    success: bool = True
    data: TopicGraphData
    message: str = "Topic knowledge graph retrieved successfully"


class TopicExtractionData(BaseModel):
    course_id: str
    units_extracted: int
    topics_created: int
    subtopics_created: int
    prerequisites_created: int
    sample_topics: list[str] = Field(default_factory=list)


class TopicExtractionResponse(BaseModel):
    success: bool = True
    data: TopicExtractionData
    message: str = "Topic extraction completed successfully"

