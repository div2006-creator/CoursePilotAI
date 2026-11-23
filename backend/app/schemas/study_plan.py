"""Pydantic schemas for Adaptive Learning Planner."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PlanItemUpdatePayload(BaseModel):
    """Payload for updating a study plan item status or attributes."""

    status: Optional[
        Literal[
            "PENDING",
            "IN_PROGRESS",
            "COMPLETED",
            "SKIPPED",
            "pending",
            "in_progress",
            "completed",
            "skipped",
        ]
    ] = None
    duration_minutes: Optional[int] = Field(default=None, ge=5, le=360)
    scheduled_date: Optional[date] = None


class StudyPlanGeneratePayload(BaseModel):
    """Payload to trigger study plan generation."""

    exam_date: Optional[date] = None
    daily_minutes: Optional[int] = Field(default=None, ge=15, le=720)
    force_regenerate: bool = False


class PlanItemResponse(BaseModel):
    """Details of a scheduled study plan item."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plan_id: UUID
    topic_id: UUID
    topic_name: str
    unit_name: Optional[str] = None
    difficulty: str = "medium"
    scheduled_date: date
    duration_minutes: int
    priority_score: float
    session_type: str
    status: str
    sequence_number: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    is_prerequisite_satisfied: bool = True
    unmet_prerequisites: List[str] = Field(default_factory=list)


class DayScheduleGroup(BaseModel):
    """Group of study sessions scheduled for a particular calendar date."""

    date: date
    day_number: int
    total_minutes: int
    is_exam_day: bool = False
    is_final_revision_day: bool = False
    sessions: List[PlanItemResponse] = Field(default_factory=list)


class StudyPlanProgress(BaseModel):
    """Aggregated completion and pace progress for a study plan."""

    total_items: int
    completed_items: int
    in_progress_items: int
    pending_items: int
    skipped_items: int
    completion_percentage: float
    total_minutes_scheduled: int
    completed_minutes: int
    days_remaining: Optional[int] = None
    target_exam_date: Optional[date] = None
    daily_minutes_target: int
    unslotted_topics_count: int = 0
    unslotted_topic_names: List[str] = Field(default_factory=list)
    is_on_track: bool = True


class StudyPlanResponseData(BaseModel):
    """Full detail view of an active or historical study plan."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    course_id: UUID
    course_title: str
    version: int
    status: str
    created_at: datetime
    exam_date: Optional[date] = None
    daily_minutes: int
    summary: Optional[str] = None
    progress: StudyPlanProgress
    days: List[DayScheduleGroup] = Field(default_factory=list)


class StudyPlanResponse(BaseModel):
    """API envelope for a single study plan."""

    success: bool = True
    data: StudyPlanResponseData
    message: str = "Study plan retrieved successfully"


class StudyPlanHistoryItem(BaseModel):
    """Summary item for past plan versions."""

    id: UUID
    course_id: UUID
    version: int
    status: str
    created_at: datetime
    exam_date: Optional[date] = None
    daily_minutes: int
    total_items: int
    completed_items: int
    completion_percentage: float


class StudyPlanHistoryResponse(BaseModel):
    """API envelope for list of historical study plans."""

    success: bool = True
    data: List[StudyPlanHistoryItem] = Field(default_factory=list)
    message: str = "Study plan history retrieved successfully"


class PlanItemResponseEnvelope(BaseModel):
    """API envelope for updated plan item."""

    success: bool = True
    data: PlanItemResponse
    message: str = "Plan item updated successfully"

