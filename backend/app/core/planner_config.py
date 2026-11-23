"""Configuration weights and constants for the Adaptive Learning Planner."""
from __future__ import annotations

from typing import Dict

# ---------------------------------------------------------------------------
# Topic Priority Calculation Weights (Must sum to 1.00)
# ---------------------------------------------------------------------------
WEIGHT_GAP_SEVERITY: float = 0.35
WEIGHT_TOPIC_IMPORTANCE: float = 0.20
WEIGHT_PREREQUISITE_IMPACT: float = 0.20
WEIGHT_TOPIC_DIFFICULTY: float = 0.10
WEIGHT_EXAM_URGENCY: float = 0.15

# Assert weight validity
assert (
    round(
        WEIGHT_GAP_SEVERITY
        + WEIGHT_TOPIC_IMPORTANCE
        + WEIGHT_PREREQUISITE_IMPACT
        + WEIGHT_TOPIC_DIFFICULTY
        + WEIGHT_EXAM_URGENCY,
        2,
    )
    == 1.00
), "Planner priority weights must sum to 1.00"

# ---------------------------------------------------------------------------
# Base Durations by Difficulty (in minutes)
# ---------------------------------------------------------------------------
BASE_DURATIONS: Dict[str, int] = {
    "easy": 30,
    "beginner": 30,
    "medium": 60,
    "intermediate": 60,
    "hard": 90,
    "advanced": 90,
}
DEFAULT_BASE_DURATION: int = 60

# ---------------------------------------------------------------------------
# Adaptive Duration Multipliers & Session Rules
# ---------------------------------------------------------------------------
# Strong mastery: light revision session only
DURATION_MULTIPLIER_STRONG: float = 0.50
# Developing mastery: focused practice session
DURATION_MULTIPLIER_DEVELOPING: float = 0.75
# Weak mastery: thorough concept learning + examples
DURATION_MULTIPLIER_WEAK_LEARN: float = 1.00
# Weak mastery: follow-up practice session
DURATION_MULTIPLIER_WEAK_PRACTICE: float = 0.75
# Not assessed: diagnostic assessment session
DURATION_ASSESSMENT_MINUTES: int = 30

# Session Types
SESSION_TYPE_LEARN: str = "LEARN"
SESSION_TYPE_PRACTICE: str = "PRACTICE"
SESSION_TYPE_REVISION: str = "REVISION"
SESSION_TYPE_ASSESSMENT: str = "ASSESSMENT"

# Status Types
STATUS_PENDING: str = "PENDING"
STATUS_IN_PROGRESS: str = "IN_PROGRESS"
STATUS_COMPLETED: str = "COMPLETED"
STATUS_SKIPPED: str = "SKIPPED"
STATUS_ACTIVE: str = "ACTIVE"
STATUS_ARCHIVED: str = "ARCHIVED"

# ---------------------------------------------------------------------------
# Scheduling Horizon & Buffer Constraints
# ---------------------------------------------------------------------------
MIN_SESSION_MINUTES: int = 15
DEFAULT_ROLLING_DAYS: int = 7
MAX_PLANNING_DAYS: int = 90
FINAL_REVISION_RESERVED_DAYS: int = 2
MIN_DAILY_STUDY_MINUTES: int = 15
MAX_DAILY_STUDY_MINUTES: int = 720
