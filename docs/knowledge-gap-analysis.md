# Part 8: Knowledge Gap Analysis & Prerequisite Intelligence

CoursePilot AI's **Knowledge Gap Analysis & Prerequisite Intelligence Engine** transforms raw diagnostic performance into structural learning insights. Rather than simply highlighting low-scoring topics, the engine traces directed dependency paths in the syllabus Knowledge Graph to uncover *why* a student struggles with advanced topics.

---

## 1. Architectural Workflow

```
[Diagnostic Assessment History]      [Syllabus Prerequisite DAG]
            │                                    │
            ▼                                    ▼
 [Topic Performance Metrics]            [Course Dependency Map]
  - Total Attempts                       - Direct & Indirect Ancestors
  - Accuracy Percentage                  - Downstream Dependent Count
  - Status (Strong/Dev/Weak/Unassessed)  - Cycle-Safe BFS Traversal
            │                                    │
            └─────────────────┬──────────────────┘
                              │
                              ▼
                [Causal Gap Classification]
                  ├── Foundational Weakness (Prerequisite failing)
                  ├── Direct Weakness (Prerequisites mastered)
                  ├── Potential Knowledge Gap (Prerequisites unassessed)
                  └── Isolated Difficulty (No failing prerequisites)
                              │
                              ▼
               [Deterministic Metrics Engine]
                  ├── Gap Severity (0 - 100)
                  ├── Confidence Score (0.0 - 1.0)
                  └── Overall Course Gap Score
                              │
                              ▼
                 [LLM Academic Explanation Layer]
                  ├── Grounded strictly on deterministic statistics
                  └── Graceful fallback to deterministic text when offline
                              │
                              ▼
                [Actionable Learning Insights]
                  ├── Deduplicated Prioritized Recommendations
                  └── One-Click Targeted Reassessment of Blindspots
```

---

## 2. Causal Classification Rules

The system evaluates weak topics ($\text{accuracy} < 50\%$) by analyzing all ancestors in the prerequisite DAG:

| Classification | Condition | Pedagogical Meaning |
| :--- | :--- | :--- |
| **Foundational Weakness** | Target is weak AND $\ge 1$ prerequisite is weak | Root cause is an earlier concept in the dependency chain. Advancing on the target topic without fixing the prerequisite will compound learning failure. |
| **Direct Weakness** | Target is weak BUT all prerequisites are strong/developing | The foundational concepts are sound. The student's difficulty is specific to the mechanics or abstractions of the target topic itself. |
| **Potential Knowledge Gap** | Target is weak AND $\ge 1$ prerequisite is unassessed | Diagnostic blindspot. The system cannot verify whether the prerequisite is strong or failing until assessed. |
| **Isolated Difficulty** | Target is weak with no prerequisites or independent | Independent concept difficulty; practice and targeted review required. |

### Worked Example:
- **Graph**: `Recursion` $\rightarrow$ `Memoization` $\rightarrow$ `Tabulation` $\rightarrow$ `Grid DP`
- **Performance**:
  - `Recursion`: 80% (Strong)
  - `Memoization`: 35% (Weak)
  - `Tabulation`: 20% (Weak)
  - `Grid DP`: 25% (Weak)
- **Conclusion**:
  - `Grid DP` and `Tabulation` are classified as **Foundational Weakness** rooted in `Memoization`.
  - `Recursion` is strong, meaning the student understands recursive branching; the roadblock is transition to state caching and iterative DP tables.

---

## 3. Deterministic Metric Calculations

All numerical evaluations are computed deterministically in Python without reliance on non-deterministic LLM scoring:

### 3.1 Gap Severity Formula
$$\text{Severity} = 0.50 \times \text{Target Weakness} + 0.30 \times \text{Prerequisite Weakness} + 0.20 \times \text{Topic Importance}$$

Where:
- $\text{Target Weakness} = 100 - \text{Target Accuracy}$
- $\text{Prerequisite Weakness} = 100 - \text{Average Prerequisite Accuracy}$ (defaults to 50 if unassessed)
- $\text{Topic Importance} = \min(100, 20 + \text{downstream\_dependents} \times 15)$

Severity is bounded in $[0.0, 100.0]$.

### 3.2 Confidence Score Formula
$$\text{Base Confidence} = \min\left(1.0, \frac{\text{Attempts}}{5}\right)$$
$$\text{Penalty} = \min(0.30, \text{Unassessed Prerequisites} \times 0.10)$$
$$\text{Confidence} = \max(0.10, \text{Base Confidence} - \text{Penalty})$$

Confidence is bounded in $[0.10, 1.00]$.

### 3.3 Overall Course Gap Score
$$\text{Overall Gap Score} = \min\left(100.0, \frac{\sum \text{Severity}_{\text{weak}}}{N_{\text{total}}} \times 1.5\right)$$

---

## 4. Graph Traversal Algorithm

The prerequisite relationship in CoursePilot AI is directed:
- `TopicPrerequisite.prerequisite_id` is the required concept.
- `TopicPrerequisite.topic_id` is the dependent concept.

To evaluate a target topic $T$:
1. Upward BFS traces all ancestral prerequisites via `prerequisite_id`.
2. A `visited` set prevents infinite loops in cyclic or malformed graphs.
3. Each traced node records its BFS `depth` and an `is_direct` flag (`depth == 1`).
4. Nodes are evaluated against the student's historical attempts to retrieve the latest accuracy percentage and knowledge status.

---

## 5. AI Explanation Layer & Safe Fallback

The LLM is strictly used as an **academic explanation layer**:
- **Prompt Grounding**: The prompt injects only verified JSON facts: topic names, accuracy scores, attempt counts, causal classifications, and traced prerequisite chains.
- **Strict Guardrails**: The LLM is forbidden from inventing scores, guessing unassessed topic grades, or modifying classifications.
- **Deterministic Fallback**: If Ollama is offline, unreachable, or returns malformed output, the system generates structured markdown summaries directly via template logic without failing the request.

---

## 6. Database Models & Schema Migration

Alembic revision `0005_knowledge_gap_analysis` introduced:

### `knowledge_gap_analyses`
- `id`: UUID (Primary Key)
- `user_id`: UUID (Foreign Key $\rightarrow$ `users.id`, `ON DELETE CASCADE`)
- `course_id`: UUID (Foreign Key $\rightarrow$ `courses.id`, `ON DELETE CASCADE`)
- `diagnostic_session_id`: UUID (Nullable, Foreign Key $\rightarrow$ `diagnostic_sessions.id`, `ON DELETE SET NULL`)
- `status`: String (`completed`, `in_progress`, `failed`)
- `overall_gap_score`: Float (Check: $0.0 \le s \le 100.0$)
- `summary`: Text
- `topic_performances`: JSONB (Complete topic metrics snapshot)
- `created_at`: DateTime (Indexed)

### `knowledge_gaps`
- `id`: UUID (Primary Key)
- `analysis_id`: UUID (Foreign Key $\rightarrow$ `knowledge_gap_analyses.id`, `ON DELETE CASCADE`)
- `topic_id`: UUID (Foreign Key $\rightarrow$ `topics.id`, `ON DELETE CASCADE`)
- `gap_type`: String (Check: `direct_weakness`, `foundational_weakness`, `potential_knowledge_gap`, `isolated_difficulty`)
- `severity`: Float (Check: $0.0 \le s \le 100.0$)
- `confidence`: Float (Check: $0.0 \le c \le 1.0$)
- `evidence`: JSONB (Attempts, accuracy, prerequisite stats)
- `recommendation`: Text
- `prerequisite_chain`: JSONB (Ordered ancestor nodes with depth & status)

---

## 7. API Endpoints

All endpoints are mounted under `/api/v1` and protected by JWT authentication:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/courses/{course_id}/knowledge-gaps/analyze` | Executes fresh graph traversal and analysis; saves records; returns full response. |
| `GET` | `/courses/{course_id}/knowledge-gaps` | Retrieves latest completed analysis for course (or 404 if not yet run). |
| `GET` | `/courses/{course_id}/knowledge-gaps/history` | Retrieves summary list of previous analyses for trend tracking. |
| `GET` | `/topics/{topic_id}/knowledge-gaps` | Inspects current knowledge gap details and prerequisite chain for a specific topic. |
| `GET` | `/courses/{course_id}/knowledge-gaps/recommendations` | Returns deduplicated, prioritized action items sorted by severity. |
| `POST` | `/courses/{course_id}/knowledge-gaps/reassess` | Launches a targeted diagnostic session targeting unassessed prerequisite topics. |

---

## 8. Automated Test Coverage

The test suite in `backend/app/tests/test_knowledge_gaps.py` verifies the entire module offline:
- Database schema and relationship cascades (`test_database.py` $\rightarrow$ 15 tests).
- Topic accuracy and status classification (`test_topic_performance_calculation`, `test_topic_knowledge_classification`).
- BFS traversal and cycle detection (`test_prerequisite_chain_tracing`).
- Downstream dependent counting (`test_count_downstream_dependents`).
- Deterministic severity and confidence calculations (`test_calculate_gap_severity`, `test_calculate_confidence_levels`).
- Causal gap classification (`test_classify_knowledge_gap_direct_weakness`, `test_classify_knowledge_gap_foundational_weakness`, `test_classify_knowledge_gap_potential_gap`, `test_classify_knowledge_gap_isolated`).
- Deduplicated recommendation generation (`test_generate_recommendations_deduplication`).
- AI explanation generation with mocked LLM and fallback on failure (`test_ai_explanation_generation`, `test_deterministic_summary_fallback`).
- API endpoint contracts and authorization isolation (`test_knowledge_gap_api_endpoints`, `test_reassess_unassessed_prerequisites_endpoint`, `test_knowledge_gap_unauthorized_access`).

**Total Backend Test Count**: 91 passing tests (100% pass rate).

