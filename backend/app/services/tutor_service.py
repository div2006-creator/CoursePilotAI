"""Personalized AI Tutor Service.

Implements session lifecycle management, multi-turn conversational tutoring,
context-grounded pedagogical state transitions, and session completion.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.ai.llm import LLMError, generate_completion
from app.agents.tools.tutor_context_tool import (
    build_tutor_context,
    format_tutor_context_prompt,
)
from app.config import settings
from app.core.database import utc_now
from app.models.course import Course
from app.models.plan_item import PlanItem
from app.models.topic import Topic
from app.models.tutor_message import (
    MSG_TYPE_CHAT,
    MSG_TYPE_EXPLANATION,
    MSG_TYPE_FEEDBACK,
    MSG_TYPE_HINT,
    MSG_TYPE_QUESTION,
    ROLE_ASSISTANT,
    ROLE_USER,
    TutorMessage,
)
from app.models.tutor_session import (
    STAGE_COMPLETED,
    STAGE_DIAGNOSIS,
    STAGE_EXAMPLE,
    STAGE_EXPLANATION,
    STAGE_PRACTICE,
    STAGE_VERIFICATION,
    STATUS_ACTIVE,
    STATUS_COMPLETED,
    STATUS_PAUSED,
    VALID_LANGUAGES,
    VALID_LEVELS,
    TutorSession,
)
from app.services.retrieval_service import retrieve_topic_context

logger = logging.getLogger(__name__)

# Load Tutor System Prompt
_PROMPT_PATH = Path(__file__).resolve().parents[1] / "agents" / "prompts" / "tutor_system_prompt.txt"
_SYSTEM_PROMPT_TEXT = None


def _get_system_prompt() -> str:
    global _SYSTEM_PROMPT_TEXT
    if _SYSTEM_PROMPT_TEXT is None:
        try:
            if _PROMPT_PATH.exists():
                _SYSTEM_PROMPT_TEXT = _PROMPT_PATH.read_text(encoding="utf-8")
            else:
                _SYSTEM_PROMPT_TEXT = "You are CoursePilot AI's personalized tutor. Guide the student with Socratic questions, verify understanding, and explain foundational concepts first."
        except Exception as exc:
            logger.warning("Error reading tutor system prompt: %s", exc)
            _SYSTEM_PROMPT_TEXT = "You are CoursePilot AI's personalized tutor."
    return _SYSTEM_PROMPT_TEXT


class TutorServiceError(Exception):
    """Base exception for AI Tutor service operations."""


class TutorSessionNotFoundError(TutorServiceError):
    """Raised when a tutoring session is not found or access is denied."""


class CourseAccessDeniedError(TutorServiceError):
    """Raised when accessing a course not owned by the user."""


# ---------------------------------------------------------------------------
# 1. Session Lifecycle Management
# ---------------------------------------------------------------------------


def start_tutor_session(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
    topic_id: uuid.UUID,
    plan_item_id: Optional[uuid.UUID] = None,
    language: str = "english",
    explanation_level: str = "intermediate",
) -> Tuple[TutorSession, TutorMessage]:
    """Initialize a new personalized tutoring session.

    Constructs verified student context, identifies prerequisite gaps,
    and generates the opening greeting and diagnostic orientation.
    """
    course = db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user_id)
    ).scalar_one_or_none()

    if not course:
        raise CourseAccessDeniedError(f"Course {course_id} not found or access denied.")

    topic = db.execute(
        select(Topic).where(Topic.id == topic_id, Topic.course_id == course_id)
    ).scalar_one_or_none()

    if not topic:
        raise TutorServiceError(f"Topic {topic_id} does not belong to course {course_id}.")

    norm_lang = language.lower() if language.lower() in VALID_LANGUAGES else "english"
    norm_level = (
        explanation_level.lower()
        if explanation_level.lower() in VALID_LEVELS
        else "intermediate"
    )

    # Create TutorSession
    session = TutorSession(
        user_id=user_id,
        course_id=course_id,
        topic_id=topic_id,
        plan_item_id=plan_item_id,
        language=norm_lang,
        explanation_level=norm_level,
        status=STATUS_ACTIVE,
        current_stage=STAGE_DIAGNOSIS,
    )
    db.add(session)
    db.flush()

    # Build student learning context
    ctx = build_tutor_context(db, user_id, session, topic)

    # Generate initial assistant greeting
    initial_text = _generate_initial_greeting(topic, ctx)

    first_message = TutorMessage(
        session_id=session.id,
        role=ROLE_ASSISTANT,
        content=initial_text,
        message_type=MSG_TYPE_CHAT,
        related_topic_id=topic.id,
        sources=ctx.sources,
    )
    db.add(first_message)
    db.commit()
    db.refresh(session)
    db.refresh(first_message)

    return session, first_message


def _generate_initial_greeting(topic: Topic, ctx: Any) -> str:
    """Generate welcoming, pedagogically grounded opening statement."""
    lang = ctx.language

    # Prerequisite gap detected
    if ctx.has_unmastered_prerequisites:
        prereqs_str = ", ".join(ctx.failing_prerequisites_names)
        if lang == "hindi":
            return (
                f"नमस्ते! आज हम {topic.name} सीखेंगे। हालांकि, मैंने देखा कि {prereqs_str} के कुछ बुनियादी कॉन्सेप्ट्स अभी पूरी तरह क्लियर नहीं हैं। "
                f"क्या आप पहले {prereqs_str} का थोड़ा रिवीजन करना चाहेंगे, या हम सीधे {topic.name} की बेसिक समझ से शुरू करें?"
            )
        elif lang == "hinglish":
            return (
                f"Hello! Aaj hum {topic.name} master karenge. Lekin pehle ek zaroori baat: maine notice kiya ki foundational concepts like {prereqs_str} abhi fully clear nahi hain. "
                f"Kya aap pehle {prereqs_str} ka quick recap chahte hain, ya direct {topic.name} ke intuition se start karein?"
            )
        else:
            return (
                f"Welcome! Today we will master **{topic.name}**. Before we dive into advanced concepts, I noticed that you have foundational knowledge gaps in: **{prereqs_str}**. "
                f"Building on shaky foundations makes advanced topics much harder. Would you like a 2-minute intuition check on {prereqs_str} first, or should we jump straight into the fundamentals of {topic.name}?"
            )

    # Strong/Ready student
    if lang == "hindi":
        return (
            f"नमस्ते! आज हम {topic.name} पर काम करेंगे। आपकी बुनियादी तैयारी बहुत अच्छी है! "
            f"शुरू करने के लिए, क्या आप मुझे संक्षेप में बता सकते हैं कि {topic.name} से आप क्या समझते हैं?"
        )
    elif lang == "hinglish":
        return (
            f"Hey! Aaj hum {topic.name} start karne wale hain. Aapka foundational base strong lag raha hai! "
            f"Start karne ke liye, kya aap briefly bata sakte ho ki {topic.name} ka basic intuition kya hai?"
        )
    else:
        return (
            f"Welcome! Today we are working on **{topic.name}** ({ctx.topic_difficulty} difficulty). Your foundational prerequisites look solid! "
            f"To kick off our session, in your own words, how would you describe the main intuition behind **{topic.name}**?"
        )


# ---------------------------------------------------------------------------
# 2. Conversational Message Exchange & State Transitions
# ---------------------------------------------------------------------------


def send_tutor_message(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    content: str,
) -> Tuple[TutorMessage, TutorSession, str, List[Dict[str, Any]]]:
    """Process student message, advance pedagogical stage, and return AI response."""
    session = get_tutor_session(db, user_id, session_id)

    clean_content = content.strip()
    if not clean_content:
        raise ValueError("Message content cannot be empty.")
    if len(clean_content) > 4000:
        raise ValueError("Message exceeds maximum length of 4000 characters.")

    topic = db.execute(select(Topic).where(Topic.id == session.topic_id)).scalar_one_or_none()
    if not topic:
        raise TutorServiceError("Associated topic not found.")

    # 1. Save user message
    user_msg = TutorMessage(
        session_id=session.id,
        role=ROLE_USER,
        content=clean_content,
        message_type=MSG_TYPE_CHAT,
        related_topic_id=topic.id,
    )
    db.add(user_msg)
    db.flush()

    # 2. Advance Teaching Stage Transition
    next_stage = _advance_teaching_stage(session.current_stage, clean_content)
    session.current_stage = next_stage

    # 3. Build verified learning context
    ctx = build_tutor_context(db, user_id, session, topic)

    # 4. Fetch recent conversation history
    history_messages = list(
        db.execute(
            select(TutorMessage)
            .where(TutorMessage.session_id == session.id)
            .order_by(TutorMessage.created_at)
        ).scalars().all()
    )

    # 5. Generate assistant response via LLM
    response_text = _generate_tutor_response(ctx, history_messages, clean_content)

    # 6. Save assistant message
    asst_msg = TutorMessage(
        session_id=session.id,
        role=ROLE_ASSISTANT,
        content=response_text,
        message_type=MSG_TYPE_EXPLANATION if next_stage == STAGE_EXPLANATION else MSG_TYPE_CHAT,
        related_topic_id=topic.id,
        sources=ctx.sources,
    )
    db.add(asst_msg)

    session.updated_at = utc_now()
    db.commit()
    db.refresh(asst_msg)
    db.refresh(session)

    # 7. Compute suggested next action
    next_action = _compute_next_action(next_stage, session)

    return asst_msg, session, next_action, ctx.sources


def _advance_teaching_stage(current_stage: str, user_text: str) -> str:
    """Transition state machine based on dialogue progression and intent."""
    text_lower = user_text.lower()

    if "practice" in text_lower or "question" in text_lower or "quiz" in text_lower or "test me" in text_lower:
        return STAGE_PRACTICE
    if "example" in text_lower or "code" in text_lower or "dry run" in text_lower or "show me" in text_lower:
        return STAGE_EXAMPLE
    if "explain" in text_lower or "understand" in text_lower or "what is" in text_lower or "why" in text_lower:
        return STAGE_EXPLANATION

    # Natural progression
    if current_stage == STAGE_DIAGNOSIS:
        return STAGE_EXPLANATION
    elif current_stage == STAGE_EXPLANATION:
        return STAGE_EXAMPLE
    elif current_stage == STAGE_EXAMPLE:
        return STAGE_PRACTICE
    elif current_stage == STAGE_PRACTICE:
        return STAGE_VERIFICATION

    return current_stage


def _compute_next_action(stage: str, session: TutorSession) -> str:
    """Provide intelligent prompt suggestions for the next step."""
    if stage == STAGE_DIAGNOSIS:
        return "Share your current understanding or ask for an overview"
    elif stage == STAGE_EXPLANATION:
        return "Ask for an example or code walkthrough"
    elif stage == STAGE_EXAMPLE:
        return "Try a practice problem"
    elif stage == STAGE_PRACTICE:
        return "Submit your answer or request a hint"
    elif stage == STAGE_VERIFICATION:
        return "Review feedback or try another problem"
    elif stage == STAGE_COMPLETED:
        return "Session completed! Head to your study roadmap"
    return "Ask any questions or request clarification"


def _generate_tutor_response(
    ctx: Any,
    history: List[TutorMessage],
    latest_query: str,
) -> str:
    """Call Ollama LLM with grounded system prompt, learning context, and dialogue history."""
    system_base = _get_system_prompt()
    context_block = format_tutor_context_prompt(ctx)
    full_system = f"{system_base}\n\n{context_block}"

    # Build dialogue transcript for prompt
    transcript_lines = []
    for m in history[-8:]:  # Keep recent 8 messages to prevent context overflow
        speaker = "Student" if m.role == ROLE_USER else "Tutor"
        transcript_lines.append(f"{speaker}: {m.content}")

    dialogue_str = "\n".join(transcript_lines)

    prompt = f"""Conversation history:
{dialogue_str}

Please respond to the student as their adaptive tutor:
- Match language: {ctx.language.upper()}
- Match explanation level: {ctx.explanation_level.upper()}
- Current stage: {ctx.current_stage}
- Ground explanations in course materials where available.
- For DSA, provide Java examples with step-by-step intuition and time/space complexity.
- End by verifying whether the student understands or asking a brief check-in question.
"""

    try:
        response = generate_completion(
            prompt=prompt,
            system=full_system,
            response_format=None,
            temperature=0.3,
            timeout=settings.OLLAMA_TIMEOUT_SECONDS,
        )
        return response.strip()
    except Exception as exc:
        logger.warning("Ollama tutor generation unavailable (%s). Returning grounded fallback.", exc)
        return _generate_fallback_response(ctx, latest_query)


def _generate_fallback_response(ctx: Any, query: str) -> str:
    """Generate high-quality grounded educational fallback response when LLM is offline."""
    t_name = ctx.topic_name
    lang = ctx.language

    if lang == "hindi":
        return (
            f"**{t_name}** को समझने के लिए सबसे पहले इसके मुख्य सिद्धांतों को देखना ज़रूरी है। "
            f"यह अवधारणा उप-समस्याओं (subproblems) को विभाजित करके हल करने पर आधारित है। "
            f"टाइम कॉम्प्लेक्सिटी को अनुकूलित करने के लिए हम पूर्व गणनाओं को सहेजते हैं।\n\n"
            f"क्या आप इसका एक संक्षिप्त कोड उदाहरण देखना चाहेंगे या कोई विशिष्ट प्रश्न पूछना चाहते हैं?"
        )
    elif lang == "hinglish":
        return (
            f"**{t_name}** ko samajhne ke liye pehle iska core idea dekhte hain. "
            f"Basically yeh problem ko smaller subproblems mein break karta hai aur unke transitions define karta hai. "
            f"Is approach se overall time complexity significantly optimize ho jaati hai.\n\n"
            f"Kya aap iska ek simple Java example dekhna chahte ho ya practice question try karna chahte ho?"
        )
    else:
        return (
            f"### Understanding {t_name}\n\n"
            f"The core principle of **{t_name}** centers on breaking a complex computational problem into smaller, well-defined state transitions. "
            f"By verifying boundary constraints and avoiding redundant computations, we achieve an optimal asymptotic bound.\n\n"
            f"**Key intuition:**\n"
            f"1. Clearly define the state parameters.\n"
            f"2. Establish the base case conditions.\n"
            f"3. Derive the transition formula.\n\n"
            f"Would you like to walk through a concrete Java example, or are you ready for a practice problem?"
        )


# ---------------------------------------------------------------------------
# 3. Querying & Preferences
# ---------------------------------------------------------------------------


def get_tutor_session(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> TutorSession:
    """Retrieve an existing tutoring session, enforcing user ownership."""
    session = db.execute(
        select(TutorSession)
        .options(
            selectinload(TutorSession.topic),
            selectinload(TutorSession.course),
            selectinload(TutorSession.messages),
        )
        .where(TutorSession.id == session_id, TutorSession.user_id == user_id)
    ).scalar_one_or_none()

    if not session:
        raise TutorSessionNotFoundError(f"Tutor session {session_id} not found or access denied.")

    return session


def get_session_messages(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> List[TutorMessage]:
    """Retrieve dialogue history for a session."""
    # Verifies ownership
    get_tutor_session(db, user_id, session_id)

    messages = list(
        db.execute(
            select(TutorMessage)
            .where(TutorMessage.session_id == session_id)
            .order_by(TutorMessage.created_at)
        ).scalars().all()
    )
    return messages


def update_tutor_preferences(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    language: Optional[str] = None,
    explanation_level: Optional[str] = None,
) -> TutorSession:
    """Update preferred language or explanation level in real time."""
    session = get_tutor_session(db, user_id, session_id)

    if language and language.lower() in VALID_LANGUAGES:
        session.language = language.lower()

    if explanation_level and explanation_level.lower() in VALID_LEVELS:
        session.explanation_level = explanation_level.lower()

    session.updated_at = utc_now()
    db.commit()
    db.refresh(session)
    return session


def complete_tutor_session(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> TutorSession:
    """Mark session completed upon evidence of understanding, updating linked study plan item."""
    session = get_tutor_session(db, user_id, session_id)

    session.status = STATUS_COMPLETED
    session.current_stage = STAGE_COMPLETED
    session.updated_at = utc_now()

    # If linked to a study plan item, update its status to COMPLETED
    if session.plan_item_id:
        plan_item = db.execute(
            select(PlanItem).where(PlanItem.id == session.plan_item_id)
        ).scalar_one_or_none()
        if plan_item:
            plan_item.status = "COMPLETED"
            plan_item.completed_at = utc_now()

    db.commit()
    db.refresh(session)
    return session

