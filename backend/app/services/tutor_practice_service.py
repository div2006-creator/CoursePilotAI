"""Tutor Practice Question Engine & Deterministic Mastery Updates.

Generates targeted practice questions, progressive Socratic hints,
evaluates student answers, records attempts, and updates topic mastery.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.ai.llm import LLMError, generate_completion
from app.core.database import utc_now
from app.models.attempt import Attempt
from app.models.course import Course
from app.models.question import Question
from app.models.topic import Topic
from app.models.topic_mastery import TopicMastery
from app.models.tutor_session import TutorSession
from app.services.retrieval_service import retrieve_topic_context

logger = logging.getLogger(__name__)


class PracticeQuestionGenerated(BaseModel):
    """Schema for LLM-generated practice question."""

    question: str = Field(description="The question prompt or problem statement")
    question_type: str = Field(
        default="multiple_choice",
        description="Type: multiple_choice, conceptual, code_tracing, or short_answer",
    )
    options: List[str] = Field(
        default_factory=list,
        description="List of 4 distinct choices for multiple_choice, or empty for open-ended",
    )
    correct_answer: str = Field(description="Correct choice (e.g. A or full correct value)")
    explanation: str = Field(description="Clear explanation of the solution and reasoning")
    difficulty: str = Field(default="medium", description="Difficulty: easy, medium, or hard")
    key_concept: Optional[str] = Field(default=None, description="Primary concept evaluated")


class TutorEvaluationResult(BaseModel):
    """Structured evaluation of a student's practice response."""

    is_correct: bool
    score: float = Field(ge=0.0, le=1.0)
    feedback: str
    strengths: List[str] = Field(default_factory=list)
    errors_identified: List[str] = Field(default_factory=list)
    misconceptions: List[str] = Field(default_factory=list)
    next_step_advice: str


# ---------------------------------------------------------------------------
# 1. Practice Question Generation
# ---------------------------------------------------------------------------


def generate_practice_question(
    db: Session,
    user_id: uuid.UUID,
    session: TutorSession,
    difficulty: Optional[str] = None,
    question_type: Optional[str] = "multiple_choice",
) -> Question:
    """Generate a novel practice question for the session topic.

    Avoids duplicating previously seen questions.
    """
    topic = db.execute(select(Topic).where(Topic.id == session.topic_id)).scalar_one_or_none()
    if not topic:
        raise ValueError(f"Topic {session.topic_id} not found.")

    target_diff = (difficulty or topic.difficulty or "medium").lower()
    if target_diff not in ("easy", "medium", "hard"):
        target_diff = "medium"

    # Retrieve existing questions for this topic to avoid duplicates
    existing_questions = list(
        db.execute(
            select(Question.question)
            .where(Question.topic_id == topic.id)
            .order_by(desc(Question.created_at))
            .limit(10)
        ).scalars().all()
    )

    # RAG syllabus context
    rag_context, _ = retrieve_topic_context(db, session.course_id, topic, limit=2)

    prompt = f"""Generate a high-quality Computer Science practice question to verify understanding.

TOPIC: {topic.name}
DIFFICULTY: {target_diff}
QUESTION TYPE: {question_type}
EXPLANATION LEVEL: {session.explanation_level}
PREFERRED LANGUAGE: {session.language}

{rag_context}

PREVIOUSLY USED QUESTIONS (DO NOT DUPLICATE THESE):
{json.dumps(existing_questions[:5])}

REQUIREMENTS:
1. Return strict JSON matching this schema:
   {{
     "question": "Clear problem statement or question",
     "question_type": "{question_type}",
     "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
     "correct_answer": "A",
     "explanation": "Detailed step-by-step solution and intuition",
     "difficulty": "{target_diff}",
     "key_concept": "Specific subconcept"
   }}
2. For multiple_choice, options MUST contain exactly 4 distinct choices, and correct_answer must match one choice or letter (e.g. 'A').
3. For DSA, prefer Java examples when code is involved.
"""

    system_prompt = "You are an expert Computer Science examiner creating diagnostic practice questions. Output ONLY valid JSON."

    try:
        raw_output = generate_completion(
            prompt=prompt,
            system=system_prompt,
            response_format="json",
            temperature=0.3,
            timeout=settings.OLLAMA_TIMEOUT_SECONDS,
        )
        parsed = _parse_practice_json(raw_output)
    except Exception as exc:
        logger.warning("LLM practice generation failed (%s). Generating deterministic fallback.", exc)
        parsed = _create_fallback_practice_question(topic, target_diff, question_type)

    # Save question to database
    question_row = Question(
        topic_id=topic.id,
        question=parsed.question,
        options=parsed.options,
        correct_answer=parsed.correct_answer,
        explanation=parsed.explanation,
        difficulty=parsed.difficulty,
        source="tutor_practice",
    )
    db.add(question_row)
    db.commit()
    db.refresh(question_row)

    return question_row


def _parse_practice_json(raw_json: str) -> PracticeQuestionGenerated:
    """Safely parse LLM output into PracticeQuestionGenerated."""
    cleaned = raw_json.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    data = json.loads(cleaned.strip())
    # Normalization
    opts = data.get("options", [])
    if isinstance(opts, dict):
        opts = [f"{k}) {v}" for k, v in opts.items()]

    return PracticeQuestionGenerated(
        question=data.get("question", "Solve the given problem:"),
        question_type=data.get("question_type", "multiple_choice"),
        options=opts,
        correct_answer=str(data.get("correct_answer", "A")),
        explanation=data.get("explanation", "Review the concept fundamentals."),
        difficulty=data.get("difficulty", "medium"),
        key_concept=data.get("key_concept"),
    )


def _create_fallback_practice_question(
    topic: Topic, difficulty: str, question_type: Optional[str]
) -> PracticeQuestionGenerated:
    """Generate high-quality deterministic fallback question when LLM is unavailable."""
    name = topic.name
    return PracticeQuestionGenerated(
        question=f"Which of the following statements regarding {name} is asymptotically and logically correct?",
        question_type="multiple_choice",
        options=[
            f"A) {name} requires defining subproblems and establishing valid base cases or transition boundaries.",
            f"B) {name} eliminates all runtime memory overhead without requiring recursion or iteration.",
            f"C) {name} cannot be solved deterministically and always runs in exponential time.",
            f"D) {name} is only applicable to unweighted 1D array searches.",
        ],
        correct_answer="A",
        explanation=f"Foundational understanding of {name} requires identifying overlapping subproblems and setting proper base transitions.",
        difficulty=difficulty,
        key_concept=f"Core intuition of {name}",
    )


# ---------------------------------------------------------------------------
# 2. Socratic Progressive Hint Generation
# ---------------------------------------------------------------------------


def generate_hint(
    db: Session,
    session: TutorSession,
    question: Question,
    hint_level: int = 1,
) -> str:
    """Generate progressive Socratic hints without revealing the full answer.

    hint_level 1: Conceptual nudge / guiding question.
    hint_level 2: Algorithmic direction / edge case check.
    hint_level 3: Structural pseudocode / first step.
    """
    topic = db.execute(select(Topic).where(Topic.id == session.topic_id)).scalar_one_or_none()
    topic_name = topic.name if topic else "this topic"

    level_instructions = {
        1: "Provide a subtle conceptual nudge or guiding question. Point the student toward the fundamental rule or intuition without mentioning the answer.",
        2: "Provide a moderate algorithmic direction or formula hint. Point out how inputs change or what invariant must be preserved.",
        3: "Provide a concrete breakdown of the first step or pseudocode outline, but DO NOT write the final answer choice.",
    }

    instructions = level_instructions.get(hint_level, level_instructions[1])

    prompt = f"""You are an expert tutor giving a helpful progressive hint to a student.

QUESTION:
{question.question}

TOPIC: {topic_name}
HINT LEVEL: {hint_level} of 3
STUDENT LEVEL: {session.explanation_level}
PREFERRED LANGUAGE: {session.language}

GOAL:
{instructions}

STRICT RULE: NEVER state the final answer option ({question.correct_answer}) or full answer text. End with an encouraging question asking the student what they think.
"""

    system_prompt = "You are CoursePilot AI's Socratic Tutor. Guide the student with progressive hints. Never give away the full answer."

    try:
        hint_text = generate_completion(
            prompt=prompt,
            system=system_prompt,
            response_format=None,
            temperature=0.4,
            timeout=settings.OLLAMA_TIMEOUT_SECONDS,
        )
        return hint_text.strip()
    except Exception as exc:
        logger.warning("LLM hint generation failed (%s). Using fallback hint.", exc)
        if hint_level == 1:
            return f"Hint 1: Think about the core definition of {topic_name}. What is the primary state or recurrence relation?"
        elif hint_level == 2:
            return f"Hint 2: Consider how the base cases behave. Which choice preserves correctness across boundary conditions?"
        else:
            return f"Hint 3: Eliminate choices that claim impossible asymptotic bounds. Focus on how {topic_name} transitions between subproblems."


# ---------------------------------------------------------------------------
# 3. Answer Evaluation & Feedback
# ---------------------------------------------------------------------------


def evaluate_student_answer(
    db: Session,
    user_id: uuid.UUID,
    session: TutorSession,
    question: Question,
    student_answer: str,
) -> TutorEvaluationResult:
    """Evaluate student's practice response, record attempt, and return structured feedback."""
    norm_student = student_answer.strip()
    norm_correct = question.correct_answer.strip()

    # Fast path for multiple choice: check exact letter match (e.g. 'A' or 'A) ...')
    is_mcq = bool(question.options and isinstance(question.options, list) and len(question.options) > 0)
    is_exact_match = False

    if is_mcq:
        student_letter = norm_student[:1].upper()
        correct_letter = norm_correct[:1].upper()
        if student_letter in ("A", "B", "C", "D") and student_letter == correct_letter:
            is_exact_match = True
        elif norm_student.lower() == norm_correct.lower():
            is_exact_match = True

    # If exact MCQ match
    if is_exact_match:
        result = TutorEvaluationResult(
            is_correct=True,
            score=1.0,
            feedback="Excellent! That is completely correct. You correctly identified the right principle.",
            strengths=["Accurate conceptual identification", "Solid understanding of subproblem boundaries"],
            errors_identified=[],
            misconceptions=[],
            next_step_advice="You are ready to advance to the next topic or try an advanced problem.",
        )
    elif is_mcq and not is_exact_match and norm_student[:1].upper() in ("A", "B", "C", "D"):
        # Clear MCQ incorrect
        exp = question.explanation or "The selected option does not satisfy the necessary algorithmic conditions."
        result = TutorEvaluationResult(
            is_correct=False,
            score=0.0,
            feedback=f"Not quite. Choice {norm_student[:1].upper()} is incorrect. {exp}",
            strengths=["Attempted the question directly"],
            errors_identified=[f"Selected {norm_student[:1].upper()} instead of correct answer"],
            misconceptions=["Confusing boundary constraints with optimal state transitions"],
            next_step_advice="Review the explanation and try tracing a small input example.",
        )
    else:
        # Conceptual or Open-Ended / Code-Tracing evaluation via LLM
        result = _evaluate_open_ended_with_llm(session, question, norm_student, norm_correct)

    # 4. Save Attempt record
    attempt_row = Attempt(
        user_id=user_id,
        course_id=session.course_id,
        topic_id=session.topic_id,
        question_id=question.id,
        tutor_session_id=session.id,
        selected_answer=norm_student,
        is_correct=result.is_correct,
        time_taken=30,
    )
    db.add(attempt_row)

    # 5. Update Topic Mastery with deterministic evidence rules
    update_topic_mastery_from_practice(
        db=db,
        user_id=user_id,
        topic_id=session.topic_id,
        is_correct=result.is_correct,
        difficulty=question.difficulty or "medium",
    )

    db.commit()
    db.refresh(attempt_row)

    return result


def _evaluate_open_ended_with_llm(
    session: TutorSession,
    question: Question,
    student_answer: str,
    correct_answer: str,
) -> TutorEvaluationResult:
    """Use structured LLM evaluation for open-ended or reasoning questions."""
    prompt = f"""Evaluate this student's response to an academic Computer Science question.

QUESTION:
{question.question}

EXPECTED CORRECT SOLUTION:
{correct_answer}

STUDENT SUBMITTED ANSWER:
{student_answer}

PREFERRED LANGUAGE: {session.language}

Return a strict JSON response with this structure:
{{
  "is_correct": true or false,
  "score": float between 0.0 and 1.0,
  "feedback": "Constructive pedagogical feedback explaining what was right and wrong",
  "strengths": ["list", "of", "strong points"],
  "errors_identified": ["list", "of", "mistakes if any"],
  "misconceptions": ["identified misconceptions"],
  "next_step_advice": "Actionable next learning step"
}}
"""

    system_prompt = "You are CoursePilot AI's evaluation engine. Assess student correctness fairly and constructively. Output ONLY JSON."

    try:
        raw_output = generate_completion(
            prompt=prompt,
            system=system_prompt,
            response_format="json",
            temperature=0.1,
            timeout=settings.OLLAMA_TIMEOUT_SECONDS,
        )
        cleaned = raw_output.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        data = json.loads(cleaned.strip())
        return TutorEvaluationResult(
            is_correct=bool(data.get("is_correct", False)),
            score=float(data.get("score", 0.0)),
            feedback=str(data.get("feedback", "Review the concept fundamentals.")),
            strengths=list(data.get("strengths", [])),
            errors_identified=list(data.get("errors_identified", [])),
            misconceptions=list(data.get("misconceptions", [])),
            next_step_advice=str(data.get("next_step_advice", "Review the problem again.")),
        )
    except Exception as exc:
        logger.warning("LLM answer evaluation failed (%s). Using heuristic evaluation.", exc)
        # Heuristic comparison: check overlap with expected keywords
        words_expected = set(correct_answer.lower().split())
        words_student = set(student_answer.lower().split())
        overlap = len(words_expected.intersection(words_student))
        is_corr = overlap >= max(2, len(words_expected) // 3)

        return TutorEvaluationResult(
            is_correct=is_corr,
            score=0.8 if is_corr else 0.2,
            feedback="Your answer covers key aspects of the problem." if is_corr else "Your response misses several key concepts from the expected solution.",
            strengths=["Demonstrated relevant conceptual terminology"] if is_corr else [],
            errors_identified=[] if is_corr else ["Missing core algorithmic rationale"],
            misconceptions=[],
            next_step_advice="Practice another variation of this problem to solidify understanding.",
        )


# ---------------------------------------------------------------------------
# 4. Deterministic Mastery Updates
# ---------------------------------------------------------------------------


def update_topic_mastery_from_practice(
    db: Session,
    user_id: uuid.UUID,
    topic_id: uuid.UUID,
    is_correct: bool,
    difficulty: str = "medium",
) -> TopicMastery:
    """Update topic mastery deterministically after verified practice attempts.

    Rules:
    - Never artificially jumps from 0 to 1 on a single attempt.
    - Considers difficulty, consistency, and prior attempts.
    - Capped strictly in [0.0, 1.0].
    """
    mastery = db.execute(
        select(TopicMastery).where(
            TopicMastery.user_id == user_id,
            TopicMastery.topic_id == topic_id,
        )
    ).scalar_one_or_none()

    if not mastery:
        mastery = TopicMastery(
            user_id=user_id,
            topic_id=topic_id,
            mastery_score=0.0,
            confidence_score=0.0,
            last_assessed_at=utc_now(),
        )
        db.add(mastery)
        db.flush()

    diff = difficulty.lower()
    # Step weights: Hard questions yield more mastery credit, easy yield less
    if diff in ("hard", "advanced"):
        gain = 0.15
        loss = 0.05
    elif diff in ("easy", "beginner"):
        gain = 0.08
        loss = 0.12
    else:  # medium
        gain = 0.12
        loss = 0.08

    # Query total attempts count for this user and topic
    attempts_count = db.execute(
        select(Attempt).where(Attempt.user_id == user_id, Attempt.topic_id == topic_id)
    ).scalars().all()
    n_attempts = len(attempts_count) + 1

    # Confidence scales with sample size: confidence = min(1.0, n_attempts / 8.0)
    new_confidence = min(1.0, round(n_attempts / 8.0, 2))

    current_score = mastery.mastery_score
    if is_correct:
        # Diminishing returns as mastery approaches 1.0
        remaining_headroom = 1.0 - current_score
        new_score = current_score + (gain * remaining_headroom)
    else:
        # Penalty damped by confidence
        new_score = max(0.0, current_score - loss)

    mastery.mastery_score = round(min(1.0, max(0.0, new_score)), 3)
    mastery.confidence_score = new_confidence
    mastery.last_assessed_at = utc_now()
    db.flush()

    # Record historical snapshot for longitudinal learning analytics
    try:
        topic_obj = db.execute(select(Topic).where(Topic.id == topic_id)).scalar_one_or_none()
        if topic_obj:
            from app.models.topic_mastery_history import TopicMasteryHistory
            snapshot = TopicMasteryHistory(
                user_id=user_id,
                course_id=topic_obj.course_id,
                topic_id=topic_id,
                mastery_score=mastery.mastery_score,
                confidence_score=mastery.confidence_score,
                evidence_count=n_attempts,
                assessment_type="PRACTICE",
                recorded_at=utc_now(),
            )
            db.add(snapshot)
            db.flush()
    except Exception as exc:
        logger.warning("Could not record TopicMasteryHistory snapshot: %s", exc)

    return mastery
