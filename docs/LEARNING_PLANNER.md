# Part 9: Adaptive Learning Planner

CoursePilot AI's **Adaptive Learning Planner** converts a student's diagnostic performance and knowledge gaps into a personalized, prerequisite-respecting study roadmap.

Rather than scheduling every topic uniformly or arbitrarily, the planner combines:
1. **Deterministic Multi-Factor Priority Scoring** (35% gap severity, 20% topic importance, 20% prerequisite impact, 10% difficulty, 15% exam urgency).
2. **Kahn's Topological Prerequisite Sorting** with cycle-safe fallback and priority tie-breaking.
3. **Adaptive Duration Estimation** based on difficulty and mastery levels.
4. **Daily Study-Time Budget Enforcement** ensuring daily minutes are never exceeded.
5. **Exam Horizon Scheduling** with a dedicated final revision buffer (1–2 days before exam) and rolling 7-day fallback when no exam date is set.
6. **Dynamic Replanning & Rebalancing** that preserves completed sessions and rebalances remaining work from today forward.

---

## 1. Architectural Workflow

```
[Diagnostic History & Gap Analysis]        [Syllabus Prerequisite DAG]
                │                                       │
                ▼                                       ▼
     [Topic Priorities (0-100)]               [In-Degree Dependencies]
      - Gap Severity: 35%                      - Direct Prerequisites
      - Topic Importance: 20%                  - Dependent Count
      - Prerequisite Impact: 20%               - Transitive Ancestors
      - Topic Difficulty: 10%
      - Exam Urgency: 15%
                │                                       │
                └───────────────────┬───────────────────┘
                                    │
                                    ▼
                    [Topological Schedulability Queue]
                     - Foundational prerequisites first
                     - Priority score tie-breaking
                                    │
                                    ▼
                    [Adaptive Duration Estimator]
                     - Weak: Learn (1.0x) + Practice (0.75x)
                     - Developing: Practice (0.75x)
                     - Strong: Revision (0.50x)
                     - Not Assessed: Assessment (30m)
                                    │
                                    ▼
                    [Calendar Day Allocation Engine]
                     - Strict daily_minutes ceiling
                     - Exam horizon boundary checks
                     - Reserved final revision window
                     - Unslotted topics detection
                                    │
                                    ▼
                    [Dynamic Rebalancer & Progress]
                     - Preserves completed items
                     - Moves pending sessions from today
                     - Re-checks mastery upgrades
```

---

## 2. Topic Priority Formula

The priority score $P \in [0, 100]$ is computed as:

$$P = 0.35 \cdot S_{\text{gap}} + 0.20 \cdot I_{\text{topic}} + 0.20 \cdot D_{\text{prereq}} + 0.10 \cdot F_{\text{diff}} + 0.15 \cdot U_{\text{exam}}$$

Where:
- **$S_{\text{gap}}$ (Gap Severity, 35%)**:
  - Weak: $\max(50.0, 100 - \text{accuracy})$.
  - Developing: $\max(25.0, 100 - \text{accuracy})$.
  - Strong: $\max(5.0, (100 - \text{accuracy}) \cdot 0.25)$.
  - Not Assessed: $60.0$ (moderate-high evaluation need).
- **$I_{\text{topic}}$ (Topic Importance, 20%)**: Downstream dependent count: $\min(100.0, 20.0 + 15.0 \cdot N_{\text{dependents}})$.
- **$D_{\text{prereq}}$ (Prerequisite Impact, 20%)**: Number of unmastered foundational requirements: $\min(100.0, 25.0 \cdot N_{\text{unmastered\_prereqs}})$.
- **$F_{\text{diff}}$ (Difficulty, 10%)**: Easy: 30, Medium: 60, Hard: 90.
- **$U_{\text{exam}}$ (Exam Urgency, 15%)**: Scaling up as days to exam decrease ($\le 7$ days: 95–100, $\le 14$ days: 80, $\le 30$ days: 60, rolling default: 50).

---

## 3. Adaptive Duration Multipliers

Base durations by topic difficulty:
- Easy / Beginner: 30 minutes
- Medium / Intermediate: 60 minutes
- Hard / Advanced: 90 minutes

Multipliers applied by mastery state:
- **Weak**: Scheduled for **LEARN** ($1.00\times$) session followed by **PRACTICE** ($0.75\times$) session.
- **Developing**: Scheduled for **PRACTICE** ($0.75\times$) session.
- **Strong**: Scheduled for light **REVISION** ($0.50\times$) session.
- **Not Assessed**: Scheduled for diagnostic **ASSESSMENT** (30 minutes).

---

## 4. Database Schema (Migration `0006`)

### `study_plans` Table
- `id` (UUID, primary key)
- `user_id` (UUID, FK -> `users.id`, index)
- `course_id` (UUID, FK -> `courses.id`, index)
- `version` (int, default 1, Check: `version >= 1`)
- `status` (string, default `'active'`, index)
- `daily_minutes` (int, default 60)
- `exam_date` (Date, nullable, index)
- `summary` (Text, nullable)
- `created_at` (DateTime, UTC)

### `plan_items` Table
- `id` (UUID, primary key)
- `plan_id` (UUID, FK -> `study_plans.id`, index)
- `topic_id` (UUID, FK -> `topics.id`, index)
- `scheduled_date` (Date, index)
- `duration_minutes` (int, Check: `duration_minutes > 0`)
- `priority_score` (float, Check: `priority_score >= 0.0 AND priority_score <= 100.0`)
- `session_type` (string, index, values: `LEARN`, `PRACTICE`, `REVISION`, `ASSESSMENT`)
- `status` (string, default `'PENDING'`, index)
- `sequence_number` (int, default 1, Check: `sequence_number >= 1`)
- `created_at` (DateTime, UTC)
- `completed_at` (DateTime, nullable)

---

## 5. API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/courses/{course_id}/study-plan/generate` | Generate or regenerate an adaptive learning plan. |
| `GET` | `/api/v1/courses/{course_id}/study-plan` | Retrieve the active plan, daily schedule, and progress. |
| `GET` | `/api/v1/study-plans/{plan_id}` | Retrieve a specific historical plan snapshot. |
| `PATCH` | `/api/v1/study-plans/{plan_id}/items/{item_id}` | Update session status (`COMPLETED`, `IN_PROGRESS`, `SKIPPED`). |
| `POST` | `/api/v1/study-plans/{plan_id}/rebalance` | Dynamically rebalance remaining sessions preserving completed work. |
| `GET` | `/api/v1/courses/{course_id}/study-plan/history` | List all historical plan versions with completion rates. |

---

## 6. Frontend Roadmap Interface

- **`PlanProgress`**: Comprehensive stats bar displaying completion percentage, scheduled vs completed study minutes, days remaining to exam, and unslotted topics warnings.
- **`StudySessionCard`**: Visual card for individual sessions with session type badge, difficulty, priority, prerequisite satisfaction warning, and action buttons (`Start`, `Complete`, `Skip`, `Restore`).
- **`StudyPlanCalendar`**: Day-by-day grouped view with calendar headers, exam day indicators, final revision buffer tags, and total daily duration budgets.
- **`StudyPlanCard`**: Vertical roadmap visualizing topological concept progression with step numbers, connection lines, and status indicators.
- **`StudyPlan` Page**: Full interactive workspace supporting course switching, plan regeneration modals, history drawer, and dynamic rebalancing.

