"""SQLAlchemy ORM models package.

Importing this package registers all CoursePilot AI models with `Base.metadata`
so Alembic can discover tables, constraints, and indexes during migration generation.
"""

from app.core.database import Base
from app.models.agent_run import AgentRun
from app.models.attempt import Attempt
from app.models.course import Course
from app.models.diagnostic_session import DiagnosticSession, DiagnosticSessionQuestion
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_gap import KnowledgeGap, KnowledgeGapAnalysis
from app.models.plan_item import PlanItem
from app.models.question import Question
from app.models.study_plan import StudyPlan
from app.models.topic import Topic
from app.models.topic_mastery import TopicMastery
from app.models.topic_mastery_history import TopicMasteryHistory
from app.models.topic_prerequisite import (
    CircularPrerequisiteError,
    TopicPrerequisite,
    validate_no_prerequisite_cycle,
)
from app.models.tutor_message import TutorMessage
from app.models.tutor_session import TutorSession
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Course",
    "Document",
    "DocumentStatus",
    "DocumentChunk",
    "Topic",
    "TopicPrerequisite",
    "CircularPrerequisiteError",
    "validate_no_prerequisite_cycle",
    "Question",
    "Attempt",
    "TopicMastery",
    "TopicMasteryHistory",
    "StudyPlan",
    "PlanItem",
    "AgentRun",
    "DiagnosticSession",
    "DiagnosticSessionQuestion",
    "KnowledgeGapAnalysis",
    "KnowledgeGap",
    "TutorSession",
    "TutorMessage",
]
