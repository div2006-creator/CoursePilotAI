"""Pydantic schemas for Learning Analytics and Adaptive Progress Intelligence."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None


# ---------------------------------------------------------------------------
# 1. Course Overview
# ---------------------------------------------------------------------------


class CourseOverviewResponseData(BaseModel):
    total_topics: int = Field(..., description="Total topics in course")
    assessed_topics: int = Field(..., description="Topics with at least one assessment attempt")
    strong_topics: int = Field(..., description="Topics with mastery >= 80%")
    developing_topics: int = Field(..., description="Topics with mastery 50-79%")
    weak_topics: int = Field(..., description="Topics with mastery < 50%")
    unassessed_topics: int = Field(..., description="Topics with zero assessment evidence")
    completed_study_sessions: int = Field(..., description="Plan items completed")
    pending_study_sessions: int = Field(..., description="Plan items pending or in progress")
    total_practice_attempts: int = Field(..., description="Total verified practice attempts")
    average_mastery_percentage: Optional[float] = Field(
        None, description="Average mastery across assessed topics, None if no topics assessed"
    )
    active_plan_id: Optional[uuid.UUID] = None
    active_plan_version: Optional[int] = None
    exam_date: Optional[str] = None
    days_remaining: Optional[int] = None


class CourseOverviewResponse(BaseResponse):
    data: CourseOverviewResponseData


# ---------------------------------------------------------------------------
# 2. Topic Mastery
# ---------------------------------------------------------------------------


class TopicMasteryItem(BaseModel):
    topic_id: uuid.UUID
    topic_name: str
    unit_name: Optional[str] = None
    difficulty: str
    mastery_score: Optional[float] = None
    mastery_percentage: Optional[float] = None
    previous_mastery_score: Optional[float] = None
    mastery_change: Optional[float] = None
    diagnostic_accuracy: Optional[float] = None
    latest_practice_accuracy: Optional[float] = None
    evidence_count: int = 0
    last_assessed_at: Optional[datetime] = None
    learning_status: str = Field(..., description="STRONG, DEVELOPING, WEAK, NOT_ASSESSED")
    is_prerequisite_satisfied: bool = True
    unmet_prerequisites: List[str] = Field(default_factory=list)
    recommended_action: str


class TopicMasteryAnalyticsResponseData(BaseModel):
    topics: List[TopicMasteryItem]
    total_count: int
    strong_count: int
    developing_count: int
    weak_count: int
    unassessed_count: int


class TopicMasteryAnalyticsResponse(BaseResponse):
    data: TopicMasteryAnalyticsResponseData


# ---------------------------------------------------------------------------
# 3. Learning Improvement & Diagnostic Comparison
# ---------------------------------------------------------------------------


class DiagnosticComparisonItem(BaseModel):
    topic_id: uuid.UUID
    topic_name: str
    unit_name: Optional[str] = None
    baseline_score: float = Field(..., description="Initial diagnostic accuracy %")
    latest_score: Optional[float] = Field(None, description="Latest fresh assessment accuracy %")
    percentage_point_improvement: Optional[float] = Field(
        None, description="Absolute percentage point delta (latest - baseline)"
    )
    baseline_questions_count: int
    latest_questions_count: int
    baseline_date: datetime
    latest_date: Optional[datetime] = None
    evidence_quality: str = Field(..., description="HIGH, MEDIUM, LOW, INSUFFICIENT")
    is_fresh: bool = Field(True, description="True if identical repeated questions were excluded")
    status_label: str


class LearningImprovementResponseData(BaseModel):
    has_sufficient_data: bool
    total_comparisons: int
    improved_topics_count: int
    stagnant_topics_count: int
    regressed_topics_count: int
    average_percentage_point_change: Optional[float] = None
    comparisons: List[DiagnosticComparisonItem]
    explanation: str


class LearningImprovementResponse(BaseResponse):
    data: LearningImprovementResponseData


# ---------------------------------------------------------------------------
# 4. Learning Velocity & Progress
# ---------------------------------------------------------------------------


class LearningVelocityData(BaseModel):
    topics_improved_7d: int
    topics_improved_30d: int
    average_mastery_change: Optional[float] = None
    transitions_weak_to_developing: int
    transitions_developing_to_strong: int
    velocity_status: str = Field(..., description="ACCELERATING, STEADY, EARLY_STAGE, NEEDS_PRACTICE")
    velocity_description: str


class LearningProgressPoint(BaseModel):
    date: str
    average_mastery: float
    assessed_topics_count: int


class LearningProgressResponseData(BaseModel):
    history_points: List[LearningProgressPoint]
    velocity: LearningVelocityData


class LearningProgressResponse(BaseResponse):
    data: LearningProgressResponseData


# ---------------------------------------------------------------------------
# 5. Study Consistency
# ---------------------------------------------------------------------------


class DailyActivityPoint(BaseModel):
    date: str
    completed_sessions: int
    practice_attempts: int
    minutes_spent: int


class StudyConsistencyResponseData(BaseModel):
    completed_sessions: int
    skipped_sessions: int
    pending_sessions: int
    total_scheduled: int
    completion_rate: float
    active_study_days: int
    current_streak_days: int
    daily_activity: List[DailyActivityPoint]
    streak_description: str


class StudyConsistencyResponse(BaseResponse):
    data: StudyConsistencyResponseData


StudyConsistencyData = StudyConsistencyResponseData


# ---------------------------------------------------------------------------
# 6. Prerequisite Bottlenecks
# ---------------------------------------------------------------------------


class PrerequisiteBlockerItem(BaseModel):
    topic_id: uuid.UUID
    topic_name: str
    unit_name: Optional[str] = None
    mastery_score: Optional[float] = None
    mastery_percentage: Optional[float] = None
    dependent_topics_count: int
    blocked_topics_names: List[str]
    bottleneck_impact_score: float
    explanation: str
    action_url: str


class PrerequisiteBottlenecksResponse(BaseResponse):
    data: List[PrerequisiteBlockerItem]


# ---------------------------------------------------------------------------
# 7. Exam Readiness Engine
# ---------------------------------------------------------------------------


class ExamReadinessResponseData(BaseModel):
    readiness_score: float = Field(..., ge=0.0, le=100.0)
    category: str = Field(..., description="Exam Ready, Almost Ready, Needs More Practice, At Risk")
    is_reliable: bool = Field(..., description="False if assessment coverage is below threshold")
    assessment_coverage_percentage: float
    coverage_warning: Optional[str] = None
    mastery_component: float
    importance_component: float
    prerequisite_component: float
    recent_performance_component: float
    coverage_component: float
    exam_date: Optional[str] = None
    days_remaining: Optional[int] = None
    strong_topics_count: int
    weak_topics_count: int
    unassessed_topics_count: int
    blocking_prerequisites_count: int
    recommended_actions: List[str]


class ExamReadinessResponse(BaseResponse):
    data: ExamReadinessResponseData


ExamReadinessData = ExamReadinessResponseData


# ---------------------------------------------------------------------------
# 8. Recommendations Engine
# ---------------------------------------------------------------------------


class RecommendationItem(BaseModel):
    id: str
    title: str
    description: str
    reason: str
    priority: str = Field(..., description="HIGH, MEDIUM, LOW")
    action_type: str = Field(..., description="TUTOR, PRACTICE, DIAGNOSTIC, STUDY_PLAN")
    action_url: str
    related_topic_id: Optional[uuid.UUID] = None
    supporting_evidence: str


class RecommendationsResponse(BaseResponse):
    data: List[RecommendationItem]


# ---------------------------------------------------------------------------
# 9. Full Analytics Dashboard
# ---------------------------------------------------------------------------


class FullAnalyticsDashboardResponseData(BaseModel):
    overview: CourseOverviewResponseData
    mastery_analytics: TopicMasteryAnalyticsResponseData
    improvement: LearningImprovementResponseData
    progress: LearningProgressResponseData
    consistency: StudyConsistencyResponseData
    exam_readiness: ExamReadinessResponseData
    bottlenecks: List[PrerequisiteBlockerItem]
    recommendations: List[RecommendationItem]


class FullAnalyticsDashboardResponse(BaseResponse):
    data: FullAnalyticsDashboardResponseData
