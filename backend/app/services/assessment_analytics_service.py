"""Service for computing diagnostic assessment analytics, topic accuracy, and difficulty breakdowns."""
from __future__ import annotations

from typing import Dict, List, Tuple
import uuid

from app.models.attempt import Attempt
from app.models.question import Question
from app.models.topic import Topic
from app.schemas.diagnostic import DifficultyBreakdownItem, TopicAccuracyItem


def calculate_diagnostic_score(correct: int, total: int) -> float:
    """Calculate overall percentage score for an assessment run."""
    if total <= 0:
        return 0.0
    return round((correct / total) * 100.0, 1)


def classify_accuracy_status(accuracy_percentage: float, total_questions: int) -> str:
    """Classify knowledge state based on accuracy percentage."""
    if total_questions == 0:
        return "not_assessed"
    if accuracy_percentage >= 75.0:
        return "strong"
    if accuracy_percentage >= 50.0:
        return "moderate"
    return "weak"


def calculate_topic_wise_accuracy(
    attempts: List[Attempt],
    topics_map: Dict[uuid.UUID, Topic],
) -> List[TopicAccuracyItem]:
    """Calculate topic-level performance metrics for a diagnostic assessment."""
    # Count totals and corrects per topic
    topic_counts: Dict[uuid.UUID, Dict[str, int]] = {
        t_id: {"total": 0, "correct": 0} for t_id in topics_map
    }

    for attempt in attempts:
        t_id = attempt.topic_id
        if t_id not in topic_counts:
            topic_counts[t_id] = {"total": 0, "correct": 0}
        topic_counts[t_id]["total"] += 1
        if attempt.is_correct:
            topic_counts[t_id]["correct"] += 1

    results: List[TopicAccuracyItem] = []
    for t_id, counts in topic_counts.items():
        total = counts["total"]
        correct = counts["correct"]
        accuracy = round((correct / total) * 100.0, 1) if total > 0 else 0.0
        status = classify_accuracy_status(accuracy, total)
        topic_name = topics_map[t_id].name if t_id in topics_map else "Unknown Topic"

        results.append(
            TopicAccuracyItem(
                topic_id=t_id,
                topic_name=topic_name,
                total_questions=total,
                correct_answers=correct,
                accuracy_percentage=accuracy,
                status=status,
            )
        )

    # Sort: assessed topics first by lowest accuracy (needing attention), then not assessed
    results.sort(
        key=lambda item: (
            0 if item.total_questions > 0 else 1,
            item.accuracy_percentage,
        )
    )
    return results


def calculate_difficulty_breakdown(
    attempts: List[Attempt],
    questions_map: Dict[uuid.UUID, Question],
) -> List[DifficultyBreakdownItem]:
    """Calculate accuracy metrics grouped by question difficulty level."""
    difficulty_order = ["easy", "medium", "hard"]
    counts: Dict[str, Dict[str, int]] = {
        d: {"total": 0, "correct": 0} for d in difficulty_order
    }

    for attempt in attempts:
        q = questions_map.get(attempt.question_id)
        diff = q.difficulty.lower() if q and q.difficulty else "medium"
        if diff not in counts:
            counts[diff] = {"total": 0, "correct": 0}
        counts[diff]["total"] += 1
        if attempt.is_correct:
            counts[diff]["correct"] += 1

    results: List[DifficultyBreakdownItem] = []
    for diff in difficulty_order:
        data = counts[diff]
        tot = data["total"]
        corr = data["correct"]
        acc = round((corr / tot) * 100.0, 1) if tot > 0 else 0.0
        results.append(
            DifficultyBreakdownItem(
                difficulty=diff,
                total=tot,
                correct=corr,
                accuracy_percentage=acc,
            )
        )

    # Include any other difficulties if present
    for diff, data in counts.items():
        if diff not in difficulty_order and data["total"] > 0:
            tot = data["total"]
            corr = data["correct"]
            acc = round((corr / tot) * 100.0, 1) if tot > 0 else 0.0
            results.append(
                DifficultyBreakdownItem(
                    difficulty=diff,
                    total=tot,
                    correct=corr,
                    accuracy_percentage=acc,
                )
            )

    return results


def identify_strong_and_weak_topics(
    topic_accuracies: List[TopicAccuracyItem],
) -> Tuple[List[str], List[str]]:
    """Partition topics into strong and weak categories for quick learner feedback."""
    strong_topics: List[str] = []
    weak_topics: List[str] = []

    for item in topic_accuracies:
        if item.total_questions == 0:
            continue
        if item.status == "strong":
            strong_topics.append(item.topic_name)
        elif item.status == "weak":
            weak_topics.append(item.topic_name)

    return strong_topics, weak_topics

