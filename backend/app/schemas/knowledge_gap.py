"""Pydantic schemas for Knowledge Gap Analysis and Prerequisite Intelligence."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TopicPerformanceMetric(BaseModel):
    """Granular diagnostic performance indicators for a single topic."""

    topic_id: UUID
    topic_name: str
    total_attempts: int
    correct_attempts: int
    accuracy_percentage: float
    knowledge_status: Literal["strong", "developing", "weak", "not_assessed"]
    confidence_score: float = Field(ge=0.0, le=1.0)
    last_attempted_at: Optional[datetime] = None
    unit_name: Optional[str] = None


class PrerequisiteNode(BaseModel):
    """A node in a traced prerequisite dependency chain."""

    topic_id: UUID
    topic_name: str
    knowledge_status: str
    accuracy_percentage: float
    depth: int = 1
    is_direct: bool = True


class KnowledgeGapDetail(BaseModel):
    """Detailed record of an identified knowledge gap."""

    id: Optional[UUID] = None
    topic_id: UUID
    topic_name: str
    gap_type: Literal[
        "direct_weakness",
        "foundational_weakness",
        "potential_knowledge_gap",
        "isolated_difficulty",
    ]
    severity: float = Field(ge=0.0, le=100.0)
    confidence: float = Field(ge=0.0, le=1.0)
    accuracy_percentage: float
    attempt_count: int
    evidence: Dict[str, Any] = Field(default_factory=dict)
    recommendation: Optional[str] = None
    prerequisite_chain: List[PrerequisiteNode] = Field(default_factory=list)


class GapRecommendationItem(BaseModel):
    """Actionable, prioritized learning advice for students."""

    priority: int
    topic_id: UUID
    topic_name: str
    action_type: Literal["revise_prerequisite", "practice_topic", "take_diagnostic"]
    reason: str
    severity: float


class KnowledgeGapAnalysisResponseData(BaseModel):
    """Full comprehensive result payload for a knowledge gap analysis."""

    analysis_id: UUID
    course_id: UUID
    diagnostic_session_id: Optional[UUID] = None
    status: str
    overall_gap_score: float
    created_at: datetime
    summary: str
    total_topics: int
    assessed_topics: int
    strong_topics_count: int
    developing_topics_count: int
    weak_topics_count: int
    unassessed_topics_count: int
    topic_performances: List[TopicPerformanceMetric]
    gaps: List[KnowledgeGapDetail]
    recommendations: List[GapRecommendationItem]


class KnowledgeGapAnalysisResponse(BaseModel):
    """API envelope for knowledge gap analysis."""

    success: bool = True
    data: KnowledgeGapAnalysisResponseData
    message: str = "Knowledge gap analysis completed successfully"


class KnowledgeGapHistoryItem(BaseModel):
    """Historical knowledge gap analysis summary item."""

    analysis_id: UUID
    course_id: UUID
    overall_gap_score: float
    weak_topics_count: int
    created_at: datetime


class KnowledgeGapHistoryResponse(BaseModel):
    """API envelope for historical analyses."""

    success: bool = True
    data: List[KnowledgeGapHistoryItem]
    message: str = "Knowledge gap history retrieved successfully"


class TopicKnowledgeGapResponse(BaseModel):
    """API envelope for single topic knowledge gap inspection."""

    success: bool = True
    data: Optional[KnowledgeGapDetail] = None
    message: str = "Topic knowledge gap details retrieved successfully"


class RecommendationsResponse(BaseModel):
    """API envelope for prioritized recommendations."""

    success: bool = True
    data: List[GapRecommendationItem]
    message: str = "Prioritized recommendations retrieved successfully"


class ReassessRequest(BaseModel):
    """Request payload to reassess unassessed prerequisites."""

    difficulty: Literal["easy", "medium", "hard", "mixed"] = "mixed"
    questions_per_topic: int = Field(default=2, ge=1, le=5)

