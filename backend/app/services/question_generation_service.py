"""Service for generating diagnostic assessment questions using local LLM inference."""
from __future__ import annotations

import json
import logging
from pathlib import Path
import re
from typing import Callable, List, Optional, Set
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.llm import (
    LLMError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
    generate_completion,
)
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.question import Question
from app.models.topic import Topic

logger = logging.getLogger(__name__)

PROMPT_FILE_PATH = (
    Path(__file__).resolve().parents[1] / "agents" / "prompts" / "question_generation_prompt.txt"
)


class QuestionGenerationError(Exception):
    """Base exception for question generation failures."""


class InvalidQuestionDataError(QuestionGenerationError):
    """Raised when the LLM generates invalid or malformed questions."""


def load_question_generation_prompt() -> str:
    """Load the question generation system prompt from disk."""
    if not PROMPT_FILE_PATH.exists():
        logger.warning(
            "Question generation prompt file not found at %s; using embedded fallback.",
            PROMPT_FILE_PATH,
        )
        return (
            "You are an academic exam creator. Generate high quality 4-option multiple choice "
            "questions with exact topic_id, options, correct_answer, explanation, and difficulty "
            "in strict JSON format."
        )
    return PROMPT_FILE_PATH.read_text(encoding="utf-8")


def clean_llm_json_output(raw_text: str) -> str:
    """Strip markdown code block markers and leading/trailing whitespace."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[len("```json"):].strip()
    elif text.startswith("```"):
        text = text[len("```"):].strip()

    if text.endswith("```"):
        text = text[:-len("```")].strip()

    return text


def parse_and_validate_questions_json(
    raw_text: str,
    allowed_topic_ids: Set[uuid.UUID],
    fallback_topic_id: Optional[uuid.UUID] = None,
    desired_difficulty: str = "mixed",
) -> List[dict]:
    """Parse JSON text from LLM and validate the schema for questions.

    Args:
        raw_text: Raw string returned from LLM.
        allowed_topic_ids: Set of valid UUIDs belonging to the course topics.
        fallback_topic_id: Default topic UUID to use if model omits or mismatches topic_id.
        desired_difficulty: Expected difficulty level ("easy", "medium", "hard", "mixed").

    Returns:
        List of validated question dictionaries.
    """
    cleaned = clean_llm_json_output(raw_text)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        # Attempt to extract json object using regex
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                raise InvalidQuestionDataError(f"Failed to parse LLM response as JSON: {exc}") from exc
        else:
            raise InvalidQuestionDataError(f"Failed to parse LLM response as JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise InvalidQuestionDataError("Expected JSON root to be an object")

    raw_questions = data.get("questions")
    if not isinstance(raw_questions, list) or len(raw_questions) == 0:
        raise InvalidQuestionDataError("LLM response contains no 'questions' array or array is empty")

    validated: List[dict] = []
    valid_difficulties = {"easy", "medium", "hard"}

    for idx, item in enumerate(raw_questions):
        if not isinstance(item, dict):
            continue

        raw_t_id = item.get("topic_id")
        target_topic_id: Optional[uuid.UUID] = None
        if raw_t_id:
            try:
                parsed_uuid = uuid.UUID(str(raw_t_id))
                if parsed_uuid in allowed_topic_ids:
                    target_topic_id = parsed_uuid
            except (ValueError, TypeError):
                pass

        if target_topic_id is None:
            if fallback_topic_id and fallback_topic_id in allowed_topic_ids:
                target_topic_id = fallback_topic_id
            elif allowed_topic_ids:
                target_topic_id = next(iter(allowed_topic_ids))
            else:
                continue

        q_text = str(item.get("question", "")).strip()
        if not q_text or len(q_text) < 5:
            continue

        raw_options = item.get("options")
        if not isinstance(raw_options, list):
            continue

        options = [str(opt).strip() for opt in raw_options if str(opt).strip()]
        # Check exactly 4 distinct options
        if len(options) != 4 or len(set(options)) != 4:
            continue

        correct_ans = str(item.get("correct_answer", "")).strip()
        if not correct_ans:
            continue

        # Match correct answer with options (case/whitespace sensitive first, then tolerant)
        matched_opt = None
        for opt in options:
            if opt == correct_ans:
                matched_opt = opt
                break
        if not matched_opt:
            for opt in options:
                if opt.lower() == correct_ans.lower():
                    matched_opt = opt
                    break

        if not matched_opt:
            # If model returned e.g. "A" or "Option A"
            opt_prefixes = ["A", "B", "C", "D"]
            for p_idx, prefix in enumerate(opt_prefixes):
                if correct_ans.upper() in (prefix, f"OPTION {prefix}") and p_idx < len(options):
                    matched_opt = options[p_idx]
                    break

        if not matched_opt:
            continue

        explanation = item.get("explanation")
        if explanation is not None:
            explanation = str(explanation).strip()

        item_diff = str(item.get("difficulty", "")).lower().strip()
        if item_diff not in valid_difficulties:
            if desired_difficulty in valid_difficulties:
                item_diff = desired_difficulty
            else:
                item_diff = "medium"

        validated.append({
            "topic_id": target_topic_id,
            "question": q_text,
            "options": options,
            "correct_answer": matched_opt,
            "explanation": explanation,
            "difficulty": item_diff,
        })

    if not validated:
        raise InvalidQuestionDataError("None of the generated questions met the validation criteria (4 distinct options, valid correct answer).")

    return validated


def get_topic_context_text(db: Session, course_id: uuid.UUID, topic: Topic) -> str:
    """Retrieve syllabus text or document chunk context relevant to the topic."""
    # First check document chunks for the course
    chunks_query = (
        select(DocumentChunk.content)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(
            Document.course_id == course_id,
            Document.status == "completed",
        )
        .limit(3)
    )
    chunks = db.execute(chunks_query).scalars().all()
    context_lines = []
    if topic.description:
        context_lines.append(f"Topic Description: {topic.description}")
    if chunks:
        context_lines.append("Reference Material Excerpts:")
        for c in chunks:
            context_lines.append(c[:500])

    return "\n".join(context_lines)


def generate_questions_for_topics(
    db: Session,
    course_id: uuid.UUID,
    topics: List[Topic],
    difficulty: str = "mixed",
    count_per_topic: int = 3,
    llm_generator: Optional[Callable[..., str]] = None,
) -> List[Question]:
    """Generate or retrieve questions for the specified topics.

    Reuses existing questions in the database when available.
    Generates new questions via local LLM inference when needed.
    """
    if not topics:
        return []

    generator = llm_generator or generate_completion
    system_prompt = load_question_generation_prompt()
    all_selected_questions: List[Question] = []
    allowed_topic_ids = {t.id for t in topics}

    for topic in topics:
        # Check existing questions
        query = select(Question).where(Question.topic_id == topic.id)
        if difficulty in {"easy", "medium", "hard"}:
            query = query.where(Question.difficulty == difficulty)

        existing_questions = list(db.execute(query).scalars().all())

        if len(existing_questions) >= count_per_topic:
            all_selected_questions.extend(existing_questions[:count_per_topic])
            continue

        needed = count_per_topic - len(existing_questions)
        all_selected_questions.extend(existing_questions)

        # Generate needed questions via LLM
        context_info = get_topic_context_text(db, course_id, topic)
        diff_instruction = (
            f"Difficulty: {difficulty}"
            if difficulty in {"easy", "medium", "hard"}
            else "Provide a balanced mix of easy, medium, and hard difficulty questions."
        )

        user_prompt = (
            f"Generate {needed} multiple choice assessment question(s) for the following topic:\n\n"
            f"Topic ID: {topic.id}\n"
            f"Topic Name: {topic.name}\n"
            f"{diff_instruction}\n"
            f"{context_info}\n\n"
            f"Output strictly valid JSON according to the required schema."
        )

        try:
            raw_response = generator(
                prompt=user_prompt,
                system=system_prompt,
                response_format="json",
                temperature=0.2,
            )
            parsed_questions = parse_and_validate_questions_json(
                raw_text=raw_response,
                allowed_topic_ids=allowed_topic_ids,
                fallback_topic_id=topic.id,
                desired_difficulty=difficulty,
            )
        except (LLMError, InvalidQuestionDataError) as exc:
            logger.error("Failed to generate questions for topic %s: %s", topic.name, exc)
            if existing_questions:
                # Fall back to whatever existing questions exist
                continue
            raise

        # Save valid new questions
        for item in parsed_questions[:needed]:
            q_obj = Question(
                topic_id=item["topic_id"],
                question=item["question"],
                options=item["options"],
                correct_answer=item["correct_answer"],
                explanation=item.get("explanation"),
                difficulty=item["difficulty"],
                source="ai_generated",
            )
            db.add(q_obj)
            db.flush()
            all_selected_questions.append(q_obj)

    return all_selected_questions

