"""Pydantic schemas for the diagnostic assessment engine."""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DiagnosticStartRequest(BaseModel):
    """Payload to start a diagnostic assessment session."""

    mode: Literal["full", "selected"] = "full"
    topic_ids: List[UUID] = Field(default_factory=list)
    difficulty: Literal["easy", "medium", "hard", "mixed"] = "mixed"
    questions_per_topic: int = Field(default=3, ge=1, le=10)


class QuestionPublicResponse(BaseModel):
    """Sanitized question payload sent to students during assessment.

    CRITICAL SECURITY RULE:
    `correct_answer` and `explanation` MUST NEVER be exposed here.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    topic_id: UUID
    topic_name: str
    question: str
    options: List[str]
    difficulty: str


class DiagnosticQuestionsResponse(BaseModel):
    """Questions returned for an active diagnostic session."""

    session_id: UUID
    course_id: UUID
    mode: str
    status: str
    total_questions: int
    questions: List[QuestionPublicResponse]


class AnswerSubmissionItem(BaseModel):
    """A single submitted question answer."""

    question_id: UUID
    selected_answer: str = Field(..., min_length=1)
    time_taken: int = Field(default=0, ge=0)


class DiagnosticSubmitRequest(BaseModel):
    """Payload submitted when a student completes an assessment."""

    answers: List[AnswerSubmissionItem] = Field(..., min_length=1)


class TopicAccuracyItem(BaseModel):
    """Topic-wise diagnostic performance breakdown."""

    topic_id: UUID
    topic_name: str
    total_questions: int
    correct_answers: int
    accuracy_percentage: float
    status: Literal["strong", "moderate", "weak", "not_assessed"]


class DifficultyBreakdownItem(BaseModel):
    """Difficulty-wise diagnostic performance breakdown."""

    difficulty: str
    total: int
    correct: int
    accuracy_percentage: float


class QuestionReviewItem(BaseModel):
    """Full question review with student answer, correct answer, and explanation."""

    model_config = ConfigDict(from_attributes=True)

    question_id: UUID
    topic_id: UUID
    topic_name: str
    question: str
    options: List[str]
    selected_answer: str
    correct_answer: str
    is_correct: bool
    explanation: Optional[str] = None
    time_taken: int = 0


class DiagnosticResultData(BaseModel):
    """Comprehensive diagnostic result analytics."""

    session_id: UUID
    course_id: UUID
    mode: str
    status: str
    score: float
    total_questions: int
    correct_answers: int
    incorrect_answers: int
    duration_seconds: int
    topic_accuracies: List[TopicAccuracyItem]
    difficulty_breakdown: List[DifficultyBreakdownItem]
    strongest_topics: List[str]
    weak_topics: List[str]
    questions_review: List[QuestionReviewItem]


class DiagnosticResultResponse(BaseModel):
    """Response envelope for diagnostic result."""

    success: bool = True
    data: DiagnosticResultData
    message: str = "Diagnostic assessment submitted successfully"


class DiagnosticHistoryItem(BaseModel):
    """Summary of a past diagnostic session."""

    session_id: UUID
    course_id: UUID
    mode: str
    status: str
    score: float
    total_questions: int
    correct_answers: int
    started_at: datetime
    completed_at: Optional[datetime] = None


class DiagnosticHistoryResponse(BaseModel):
    """Response envelope for diagnostic history."""

    success: bool = True
    data: List[DiagnosticHistoryItem]
    message: str = "Diagnostic history retrieved successfully"

