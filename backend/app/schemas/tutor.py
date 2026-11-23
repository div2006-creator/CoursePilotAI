"""Pydantic schemas for Part 10: Personalized AI Tutor."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TutorSessionCreatePayload(BaseModel):
    """Payload to start a personalized tutoring session."""

    topic_id: UUID
    plan_item_id: Optional[UUID] = None
    language: Optional[Literal["english", "hindi", "hinglish"]] = "english"
    explanation_level: Optional[Literal["beginner", "intermediate", "advanced"]] = "intermediate"


class TutorPreferencesUpdatePayload(BaseModel):
    """Payload to adjust language and explanation level during a session."""

    language: Optional[Literal["english", "hindi", "hinglish"]] = None
    explanation_level: Optional[Literal["beginner", "intermediate", "advanced"]] = None


class TutorMessageSendPayload(BaseModel):
    """Payload to send a message to the AI tutor."""

    message: str = Field(min_length=1, max_length=4000)


class TutorMessageItem(BaseModel):
    """A single turn in the tutoring conversation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    role: str
    content: str
    message_type: str
    related_topic_id: Optional[UUID] = None
    sources: Optional[Any] = None
    created_at: datetime


class TutorSessionResponseData(BaseModel):
    """Full detail of a tutoring session and its state."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    course_id: UUID
    course_title: Optional[str] = None
    topic_id: UUID
    topic_name: Optional[str] = None
    plan_item_id: Optional[UUID] = None
    language: str
    explanation_level: str
    status: str
    current_stage: str
    created_at: datetime
    updated_at: datetime
    suggested_next_action: Optional[str] = None
    messages: List[TutorMessageItem] = Field(default_factory=list)


class TutorSessionResponse(BaseModel):
    """Envelope for single tutor session."""

    success: bool = True
    data: TutorSessionResponseData
    message: str = "Tutor session retrieved successfully"


class TutorMessageResponseData(BaseModel):
    """Assistant response payload with stage metadata and citations."""

    message: TutorMessageItem
    session_id: UUID
    current_stage: str
    suggested_next_action: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)


class TutorMessageResponse(BaseModel):
    """Envelope for message submission result."""

    success: bool = True
    data: TutorMessageResponseData
    message: str = "Message processed successfully"


class TutorMessageListResponse(BaseModel):
    """Envelope for message history."""

    success: bool = True
    data: List[TutorMessageItem] = Field(default_factory=list)
    message: str = "Message history retrieved successfully"


class PracticeQuestionResponseData(BaseModel):
    """Targeted practice question (answers hidden before submission)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    topic_id: UUID
    topic_name: str
    question: str
    options: List[str] = Field(default_factory=list)
    difficulty: str


class PracticeQuestionResponse(BaseModel):
    """Envelope for practice question generation."""

    success: bool = True
    data: PracticeQuestionResponseData
    message: str = "Practice question generated successfully"


class PracticeAnswerSubmitPayload(BaseModel):
    """Payload to submit answer for a practice question."""

    answer: str = Field(min_length=1, max_length=2000)


class PracticeEvaluationResponseData(BaseModel):
    """Evaluation feedback with explanations, strengths, and errors."""

    question_id: UUID
    is_correct: bool
    score: float
    feedback: str
    correct_answer: str
    explanation: Optional[str] = None
    strengths: List[str] = Field(default_factory=list)
    errors_identified: List[str] = Field(default_factory=list)
    misconceptions: List[str] = Field(default_factory=list)
    next_step_advice: str


class PracticeEvaluationResponse(BaseModel):
    """Envelope for practice answer evaluation."""

    success: bool = True
    data: PracticeEvaluationResponseData
    message: str = "Answer evaluated successfully"


class HintRequestPayload(BaseModel):
    """Payload to request progressive Socratic hints."""

    hint_level: int = Field(default=1, ge=1, le=3)


class HintResponseData(BaseModel):
    """Hint payload."""

    question_id: UUID
    hint_level: int
    hint: str


class HintResponse(BaseModel):
    """Envelope for hint response."""

    success: bool = True
    data: HintResponseData
    message: str = "Hint generated successfully"

