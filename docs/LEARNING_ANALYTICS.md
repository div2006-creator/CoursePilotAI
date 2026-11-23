# Part 11: Learning Analytics & Adaptive Progress Intelligence

CoursePilot AI's **Learning Analytics and Adaptive Progress Intelligence** module provides explainable, deterministic progress tracking and honest exam readiness predictions.

Unlike typical educational dashboards that fabricate engagement streaks, inflate mastery percentages, or use non-deterministic LLM guessing, CoursePilot AI's analytics engine operates strictly on real database records, verified assessment attempts, and topological prerequisite graphs.

---

## 1. Core Principles & Design Guarantees

1. **100% Deterministic Python Calculations**: Scores, percentages, streaks, velocity classifications, and exam readiness indices are computed with pure mathematical functions. LLMs are never used for metric generation or statistical calculation.
2. **Honest Baseline vs. Fresh Assessment Comparison**: Post-learning improvement is verified by comparing diagnostic baselines against *fresh* assessment questions. Repeated or duplicate questions are strictly excluded so the score reflects genuine concept retention rather than memorization.
3. **No Fabricated Data**:
   - Zero-attempt topics are represented explicitly as `null` ("Not Assessed"), never assumed to be 0% mastery.
   - If no exam date is set, days remaining is returned as `null` without synthetic countdowns.
   - If no study sessions were completed today or yesterday, the active streak returns `0`.
4. **Data Isolation & User Authorization**: All queries, snapshots, and evaluations are strictly isolated to the authenticated user and their owned courses. Cross-user data leakage is rejected with HTTP 404/403.

---

## 2. Architecture & Data Flow

```
                      [ Diagnostic Sessions ]         [ Tutor Practice Attempts ]
                                 │                                 │
                                 ▼                                 ▼
                     [ Diagnostic Baseline ]             [ Fresh Attempts ]
                     (Earliest question set)            (Excluding baseline Qs)
                                 │                                 │
                                 └─────────────────┬───────────────┘
                                                   │
                                                   ▼
                                   [ Learning Improvement Engine ]
                                    - Percentage point change (pp)
                                    - Evidence count & quality
                                    - Exclude repeated question bias
                                                   │
   [ Topic Mastery Snapshots ]                     ▼
  (TopicMasteryHistory table) ────────► [ Longitudinal Velocity ]
                                         - 7d / 30d topic momentum
                                         - Weak -> Developing -> Strong
                                                   │
   [ Prerequisite Graph (DAG) ]                    ▼
   (In/Out degree, importance) ────────► [ Exam Readiness Engine ]
                                         - 40% Topic Mastery
                                         - 20% Topic Importance
                                         - 15% Prerequisite Health
                                         - 15% Recent Form (last 20 attempts)
                                         - 10% Assessment Coverage
                                         - Reliable threshold: >= 40% coverage
                                                   │
   [ Study Plan Items ]                            ▼
   (Status, duration, completed_at) ───► [ Consistency & Streaks ]
                                         - Honest consecutive days
                                         - Daily minutes & completion rate
                                                   │
                                                   ▼
                                     [ Unified Analytics API ]
                                     (/api/v1/courses/{id}/analytics/*)
                                                   │
                                                   ▼
                                    [ React Analytics Dashboard ]
                                    (Area charts, bars, tables, cards)
```

---

## 3. Verified Learning Improvement Methodology

### Duplicate Question Exclusion
When students review material with the AI Tutor, they might encounter practice problems. If the system were to test students on the exact same questions from their baseline diagnostic, scores would measure rote recognition.

To prevent this:
1. Baseline question IDs for each topic are extracted from the user's earliest completed diagnostic session:
   $$Q_{\text{baseline}} = \{ q.id \mid q \in \text{InitialDiagnosticSession} \}$$
2. Subsequent attempts for that topic are partitioned into duplicate and fresh:
   $$Q_{\text{fresh}} = \{ a \mid a.\text{topic\_id} = t \land a.\text{question\_id} \notin Q_{\text{baseline}} \}$$
3. The post-learning accuracy is calculated exclusively over $Q_{\text{fresh}}$:
   $$\text{LatestAccuracy} = \frac{\sum_{a \in Q_{\text{fresh}}} \mathbb{I}(a.\text{is\_correct})}{|Q_{\text{fresh}}|}$$
4. Verified Improvement:
   $$\Delta_{\text{improvement}} = \text{LatestAccuracy} - \text{BaselineAccuracy}$$
5. Evidence Quality:
   - **HIGH**: $|Q_{\text{baseline}}| \ge 3$ and $|Q_{\text{fresh}}| \ge 3$.
   - **MEDIUM**: $|Q_{\text{baseline}}| \ge 1$ and $|Q_{\text{fresh}}| \ge 2$.
   - **LOW**: $|Q_{\text{baseline}}| \ge 1$ and $|Q_{\text{fresh}}| = 1$.
   - **INSUFFICIENT**: $|Q_{\text{fresh}}| = 0$ (fresh assessment pending).

---

## 4. Exam Readiness Engine

The Exam Readiness index $R \in [0, 100]$ combines five weighted components:

$$R = 0.40 \cdot C_{\text{mastery}} + 0.20 \cdot C_{\text{importance}} + 0.15 \cdot C_{\text{prereqs}} + 0.15 \cdot C_{\text{recent}} + 0.10 \cdot C_{\text{coverage}}$$

| Component | Weight | Calculation |
| :--- | :--- | :--- |
| **Topic Mastery** | 40% | Average mastery score across all assessed course topics $\times 100$. |
| **Topic Importance** | 20% | Weighted average mastery where topics with multiple downstream dependents receive structural weights: $w_t = 1.0 + 0.5 \cdot \text{deg}^+(t)$. |
| **Prerequisite Health** | 15% | Percentage of course prerequisites where the required foundational topic is mastered ($\ge 80\%$). |
| **Recent Performance** | 15% | Accuracy across the student's 20 most recent practice/diagnostic attempts. |
| **Syllabus Coverage** | 10% | Percentage of course topics that have at least one verified assessment record. |

### Reliability Coverage Threshold
- **Coverage $\ge 40\%$**: `is_reliable = True`. Readiness score reflects meaningful course-wide assessment.
- **Coverage $< 40\%$**: `is_reliable = False`. A prominent warning banner alerts the student that the score is preliminary and encourages completing targeted diagnostics.

### Readiness Categories
- **Exam Ready** ($\ge 80.0$): Student demonstrates broad topic mastery, strong prerequisite foundations, and consistent recent accuracy.
- **Almost Ready** ($65.0 - 79.9$): Minor developing concepts remaining; final revision buffer recommended.
- **Needs More Practice** ($45.0 - 64.9$): Foundational gaps or low syllabus coverage; requires guided study plan execution.
- **At Risk** ($< 45.0$): Critical knowledge bottlenecks present; urgent foundational tutor sessions advised.

---

## 5. Learning Velocity & Milestone Graduations

Longitudinal velocity tracks the rate of topic progress over time using the `topic_mastery_history` audit table.

- **Milestone Transitions**:
  - `transitions_weak_to_developing`: Number of topics whose historical score started $< 50\%$ and advanced to $\ge 50\%$.
  - `transitions_developing_to_strong`: Number of topics whose historical score started $< 80\%$ and reached $\ge 80\%$.
- **Velocity Classifications**:
  - `ACCELERATING`: $\ge 3$ topics improved in the last 7 days or average delta $\ge +20.0$ percentage points.
  - `STEADY`: $\ge 1$ topic improved in the last 7 days or $\ge 2$ improved in the last 30 days.
  - `EARLY_STAGE`: Initial snapshots recorded; ongoing practice needed to establish momentum.
  - `NEEDS_PRACTICE`: Insufficient recent historical evidence.

---

## 6. Honest Study Consistency & Streak Algorithm

Streaks are defined strictly as **unbroken consecutive calendar days** with recorded learning activity:
1. Collect all distinct calendar dates with at least one completed study plan item or verified practice attempt:
   $$\mathcal{D}_{\text{active}} = \{ \text{date}(item.\text{completed\_at}) \} \cup \{ \text{date}(attempt.\text{created\_at}) \}$$
2. Check anchor:
   - If $\text{today} \in \mathcal{D}_{\text{active}}$, anchor date is $\text{today}$.
   - Else if $\text{yesterday} \in \mathcal{D}_{\text{active}}$, anchor date is $\text{yesterday}$ (today is still eligible to continue the streak).
   - Otherwise, active streak is **0**.
3. Count consecutive preceding days backwards from anchor until a gap is encountered.

---

## 7. Prerequisite Bottleneck Detection

Identifies foundational topics that act as learning blockers:

$$\text{ImpactScore}(t) = N_{\text{dependents}}(t) \cdot (1.0 - \text{Mastery}(t)) \cdot 10.0$$

A topic is flagged as a bottleneck if:
1. It has at least one dependent topic ($N_{\text{dependents}} \ge 1$), AND
2. Its mastery is either unassessed (`null`) or weak ($< 50\%$).

Bottlenecks are ordered descending by impact score and provide direct navigation to tutor that prerequisite concept first.

---

## 8. API Reference

All endpoints require JWT Bearer authorization and verify course ownership:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/courses/{course_id}/analytics/overview` | Course overview, topic counts, study plan progress, average mastery. |
| `GET` | `/api/v1/courses/{course_id}/analytics/mastery` | Full topic table with scores, deltas, evidence counts, and prerequisite status. |
| `GET` | `/api/v1/courses/{course_id}/analytics/improvement` | Baseline diagnostic vs fresh assessment comparison (excluding duplicates). |
| `GET` | `/api/v1/courses/{course_id}/analytics/progress` | Longitudinal mastery history points and learning velocity data. |
| `GET` | `/api/v1/courses/{course_id}/analytics/consistency` | Honest consecutive streaks, daily minutes, and completed study sessions. |
| `GET` | `/api/v1/courses/{course_id}/analytics/exam-readiness` | 5-component readiness score, category, and reliability threshold warnings. |
| `GET` | `/api/v1/courses/{course_id}/analytics/bottlenecks` | Foundational prerequisite blockers with impact scores and direct tutor links. |
| `GET` | `/api/v1/courses/{course_id}/analytics/recommendations` | Prioritized, explainable next actions (TUTOR, PRACTICE, DIAGNOSTIC, STUDY_PLAN). |
| `GET` | `/api/v1/courses/{course_id}/analytics/dashboard` | Unified payload aggregating all 8 analytics dimensions in a single request. |

---

## 9. Frontend Dashboard Components

Located in `frontend/src/components/dashboard/`:

1. `LearningOverview.tsx`: Coverage meter, average mastery, completed study sessions, practice attempts, and exam countdown.
2. `MasteryDistribution.tsx`: Color-coded stacked distribution bar (Strong $\ge 80\%$, Developing $50-79\%$, Weak $< 50\%$, Unassessed) with category cards.
3. `LearningProgressChart.tsx`: Recharts longitudinal AreaChart with gradient fill, velocity momentum badge, and graduation transition counters.
4. `TopicMasteryTable.tsx`: Searchable, filterable (All, Strong, Developing, Weak, Unassessed), sortable table with status badges and quick tutor actions.
5. `ImprovementComparison.tsx`: Diagnostic baseline vs fresh assessment comparison cards with percentage point delta badges and evidence quality indicators.
6. `ExamReadinessCard.tsx`: Readiness score dial, category badge, 5 component breakdown bars, low-coverage warning, and booster recommendations.
7. `StudyConsistency.tsx`: Habit tracking with flame streak badge, plan completion rate, and daily minutes Recharts BarChart.
8. `BottleneckCard.tsx`: Knowledge graph blockers showing weak concepts blocking downstream topics with impact scores and direct link to tutor.
9. `RecommendationList.tsx`: Prioritized next action cards with title, description, reason, supporting evidence, and direct action routing.
10. `AnalyticsPage.tsx`: Top-level responsive page with course selector dropdown, refresh action, and responsive category tabs.

