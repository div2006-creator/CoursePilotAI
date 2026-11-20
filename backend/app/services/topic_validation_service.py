"""Validation and normalization service for AI-generated topic structures and prerequisite DAGs."""
from __future__ import annotations

from collections import defaultdict, deque
import json
import logging
import re
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TopicValidationError(ValueError):
    """Raised when extracted topic structures fail schema or sanity validation."""


class ValidatedSubtopic(BaseModel):
    name: str
    description: Optional[str] = None


class ValidatedTopic(BaseModel):
    name: str
    description: Optional[str] = None
    difficulty: str = "medium"
    source_type: str = "explicit"
    source_pages: list[int] = Field(default_factory=list)
    unit_name: Optional[str] = None
    subtopics: list[ValidatedSubtopic] = Field(default_factory=list)


class ValidatedPrerequisite(BaseModel):
    topic_name: str
    prerequisite_name: str
    confidence: float = 1.0
    reason: Optional[str] = None


class ValidatedTopicExtractionResult(BaseModel):
    units: list[str] = Field(default_factory=list)
    topics: list[ValidatedTopic] = Field(default_factory=list)
    prerequisites: list[ValidatedPrerequisite] = Field(default_factory=list)


def clean_json_markdown(raw_text: str) -> str:
    """Strip markdown code block fences and surrounding whitespace."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def normalize_topic_name(name: str) -> str:
    """Normalize whitespace and strip leading list markers or bullets."""
    if not name:
        return ""
    # Collapse multiple whitespace characters
    cleaned = re.sub(r"\s+", " ", name.strip())
    # Strip leading bullet points or numbers like "1. ", "• ", "- "
    cleaned = re.sub(r"^([0-9]+\.|\*|-|•)\s*", "", cleaned)
    return cleaned.strip()


def normalize_difficulty(difficulty: Optional[str]) -> str:
    """Normalize difficulty to 'easy', 'medium', or 'hard'."""
    if not difficulty:
        return "medium"
    diff_lower = difficulty.strip().lower()
    if "easy" in diff_lower or "beginner" in diff_lower or "basic" in diff_lower:
        return "easy"
    if "hard" in diff_lower or "advanced" in diff_lower or "expert" in diff_lower:
        return "hard"
    return "medium"


def detect_prerequisite_cycles(edges: list[tuple[str, str]]) -> bool:
    """Detect if directed prerequisite edges contain a cycle.

    Edge format: `(prereq, dependent)` means `prereq -> dependent`.
    Returns True if a cycle exists, False if the graph is a DAG.
    """
    adjacency: dict[str, set[str]] = defaultdict(set)
    nodes: set[str] = set()

    for u, v in edges:
        nodes.add(u)
        nodes.add(v)
        if u == v:
            return True  # Self loop is a cycle
        adjacency[u].add(v)

    # 0 = unvisited, 1 = visiting (on current DFS stack), 2 = visited
    state: dict[str, int] = {node: 0 for node in nodes}

    def has_cycle_dfs(curr: str) -> bool:
        state[curr] = 1
        for neighbor in adjacency.get(curr, ()):
            if state[neighbor] == 1:
                return True
            if state[neighbor] == 0:
                if has_cycle_dfs(neighbor):
                    return True
        state[curr] = 2
        return False

    for node in nodes:
        if state[node] == 0:
            if has_cycle_dfs(node):
                return True

    return False


def remove_duplicate_topics(
    raw_topics: list[dict[str, Any]],
    unit_name: Optional[str] = None,
) -> list[ValidatedTopic]:
    """Deduplicate topics within a unit, merging subtopics and page references."""
    seen: dict[str, ValidatedTopic] = {}

    for t in raw_topics:
        raw_name = t.get("name", "")
        clean_name = normalize_topic_name(raw_name)
        if not clean_name:
            continue

        lookup_key = clean_name.lower()
        desc = (t.get("description") or "").strip() or None
        diff = normalize_difficulty(t.get("difficulty"))
        src_type = t.get("source_type", "explicit")
        if src_type not in ("explicit", "inferred"):
            src_type = "explicit"

        raw_pages = t.get("source_pages", [])
        clean_pages: list[int] = []
        if isinstance(raw_pages, list):
            for p in raw_pages:
                if isinstance(p, int) and p > 0:
                    clean_pages.append(p)
                elif isinstance(p, str) and p.isdigit() and int(p) > 0:
                    clean_pages.append(int(p))
        clean_pages = sorted(list(set(clean_pages)))

        raw_subtopics = t.get("subtopics", [])
        subtopic_objs: list[ValidatedSubtopic] = []
        if isinstance(raw_subtopics, list):
            sub_seen: set[str] = set()
            for sub in raw_subtopics:
                if isinstance(sub, dict):
                    s_name = normalize_topic_name(sub.get("name", ""))
                    s_desc = (sub.get("description") or "").strip() or None
                elif isinstance(sub, str):
                    s_name = normalize_topic_name(sub)
                    s_desc = None
                else:
                    continue

                if s_name and s_name.lower() not in sub_seen:
                    sub_seen.add(s_name.lower())
                    subtopic_objs.append(ValidatedSubtopic(name=s_name, description=s_desc))

        if lookup_key in seen:
            existing = seen[lookup_key]
            # Merge descriptions if existing is empty
            if not existing.description and desc:
                existing.description = desc
            # Merge page references
            existing.source_pages = sorted(list(set(existing.source_pages + clean_pages)))
            # Merge subtopics
            existing_sub_names = {s.name.lower() for s in existing.subtopics}
            for sub in subtopic_objs:
                if sub.name.lower() not in existing_sub_names:
                    existing.subtopics.append(sub)
                    existing_sub_names.add(sub.name.lower())
        else:
            topic_obj = ValidatedTopic(
                name=clean_name,
                description=desc,
                difficulty=diff,
                source_type=src_type,
                source_pages=clean_pages,
                unit_name=unit_name,
                subtopics=subtopic_objs,
            )
            seen[lookup_key] = topic_obj

    return list(seen.values())


def validate_prerequisites(
    raw_prereqs: list[dict[str, Any]],
    known_topic_names: set[str],
) -> list[ValidatedPrerequisite]:
    """Validate prerequisite relationships, rejecting missing topics, self-loops, and cycles.

    Edge direction: `prerequisite -> topic` (prerequisite is required before topic).
    """
    lookup = {name.lower(): name for name in known_topic_names}
    validated: list[ValidatedPrerequisite] = []
    edges: list[tuple[str, str]] = []  # (prereq_lower, topic_lower)

    for p in raw_prereqs:
        if not isinstance(p, dict):
            continue

        raw_topic = normalize_topic_name(p.get("topic", ""))
        raw_prereq = normalize_topic_name(p.get("prerequisite", ""))

        if not raw_topic or not raw_prereq:
            continue

        topic_key = raw_topic.lower()
        prereq_key = raw_prereq.lower()

        # Reject self-prerequisites
        if topic_key == prereq_key:
            logger.warning("Rejected self-prerequisite: %s -> %s", raw_prereq, raw_topic)
            continue

        # Both must exist in known topics
        if topic_key not in lookup or prereq_key not in lookup:
            logger.warning(
                "Skipping prerequisite with unknown topic reference: %r -> %r",
                raw_prereq,
                raw_topic,
            )
            continue

        actual_topic_name = lookup[topic_key]
        actual_prereq_name = lookup[prereq_key]

        # Check for duplicate edge
        if (prereq_key, topic_key) in edges:
            continue

        # Validate confidence score between 0.0 and 1.0
        conf_raw = p.get("confidence", 1.0)
        try:
            confidence = float(conf_raw)
            confidence = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            confidence = 1.0

        reason = (p.get("reason") or "").strip() or None

        # Check whether adding (prereq_key, topic_key) creates a cycle
        test_edges = edges + [(prereq_key, topic_key)]
        if detect_prerequisite_cycles(test_edges):
            logger.warning(
                "Cycle detected; dropping prerequisite link: %r -> %r",
                actual_prereq_name,
                actual_topic_name,
            )
            continue

        edges.append((prereq_key, topic_key))
        validated.append(
            ValidatedPrerequisite(
                topic_name=actual_topic_name,
                prerequisite_name=actual_prereq_name,
                confidence=confidence,
                reason=reason,
            )
        )

    return validated


def validate_extracted_topics(raw_content: Any) -> ValidatedTopicExtractionResult:
    """Parse and validate raw AI extraction output into a sanitized topic hierarchy and DAG."""
    if isinstance(raw_content, str):
        cleaned = clean_json_markdown(raw_content)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise TopicValidationError(
                f"AI topic extraction output is not valid JSON: {exc}"
            ) from exc
    elif isinstance(raw_content, dict):
        data = raw_content
    else:
        raise TopicValidationError("Expected dict or JSON string for topic extraction validation")

    units_data = data.get("units")
    if not isinstance(units_data, list):
        # Fallback if raw JSON has a top-level "topics" list without units
        if isinstance(data.get("topics"), list):
            units_data = [
                {
                    "unit_name": "General Syllabus",
                    "unit_title": "Core Topics",
                    "topics": data["topics"],
                }
            ]
        else:
            raise TopicValidationError("Extracted JSON must contain a 'units' or 'topics' list")

    all_topics: list[ValidatedTopic] = []
    unit_names_list: list[str] = []
    known_topic_names: set[str] = set()

    for u_idx, u in enumerate(units_data, start=1):
        if not isinstance(u, dict):
            continue

        unit_label = (u.get("unit_name") or f"Unit {u_idx}").strip()
        unit_title = (u.get("unit_title") or "").strip()
        full_unit_name = f"{unit_label}: {unit_title}".strip(" :") if unit_title else unit_label

        if full_unit_name not in unit_names_list:
            unit_names_list.append(full_unit_name)

        raw_topics = u.get("topics", [])
        if isinstance(raw_topics, list):
            unit_topics = remove_duplicate_topics(raw_topics, unit_name=full_unit_name)
            for t in unit_topics:
                # Global course deduplication across units
                if t.name.lower() in {x.name.lower() for x in all_topics}:
                    # Merge subtopics and pages into existing
                    existing = next(x for x in all_topics if x.name.lower() == t.name.lower())
                    existing.source_pages = sorted(
                        list(set(existing.source_pages + t.source_pages))
                    )
                    existing_subs = {s.name.lower() for s in existing.subtopics}
                    for sub in t.subtopics:
                        if sub.name.lower() not in existing_subs:
                            existing.subtopics.append(sub)
                            existing_subs.add(sub.name.lower())
                else:
                    all_topics.append(t)
                    known_topic_names.add(t.name)

    raw_prereqs = data.get("prerequisites", [])
    if not isinstance(raw_prereqs, list):
        raw_prereqs = []

    prerequisites = validate_prerequisites(raw_prereqs, known_topic_names)

    return ValidatedTopicExtractionResult(
        units=unit_names_list,
        topics=all_topics,
        prerequisites=prerequisites,
    )

