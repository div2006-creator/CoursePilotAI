# Part 7: Diagnostic Assessment Engine

The **Diagnostic Assessment Engine** in CoursePilot AI evaluates a student's foundational knowledge of course topics through AI-generated or syllabus-aligned multiple choice questions (MCQs), measures topic-wise conceptual strength, and stores granular attempts for future adaptive study planning.

---

## 1. Architectural Workflow

```
[Course Topics & Syllabus Chunks]
               │
               ▼
   [Question Generation Service]
      ├── Reuse existing vetted DB questions
      └── If needed, generate 4-option MCQs via local Ollama LLM
               │
               ▼
      [DiagnosticSession Created]
      (status: 'in_progress', questions linked via DiagnosticSessionQuestion)
               │
               ▼
[GET /api/v1/diagnostic/{id}/questions]
      (SECURITY: Sanitized public payload - NO correct_answer or explanation)
               │
               ▼
     [Interactive Student UI]
      ├── QuestionCard (4 distinct options: A, B, C, D)
      ├── QuestionNavigation palette with answered tracking
      ├── Live AssessmentTimer & AssessmentProgress bar
      └── SubmitConfirmationModal (warns on unanswered questions)
               │
               ▼
[POST /api/v1/diagnostic/{id}/submit]
      ├── Server-side validation of question IDs
      ├── Answer correctness evaluation: selected_answer == correct_answer
      ├── Granular Attempt records created with time_taken & is_correct
      ├── Session finalized (status: 'completed', score computed)
               │
               ▼
 [Assessment Analytics & Results]
      ├── Overall Score % (correct / total * 100)
      ├── Topic-wise Accuracy (Strong >= 75%, Moderate 50-74%, Weak < 50%)
      ├── Difficulty breakdown (Easy, Medium, Hard)
      └── Comprehensive Question-by-Question Review with Explanations
```

---

## 2. Security and Anti-Cheating Guarantees

1. **Answer & Explanation Isolation**:
   - The question retrieval endpoint (`GET /api/v1/diagnostic/{id}/questions`) and public schemas strictly omit `correct_answer` and `explanation`.
   - Inspection of client network traffic or browser dev tools reveals no answers or hints.
2. **Authoritative Server-Side Evaluation**:
   - The frontend never submits `is_correct` or `score`.
   - The server compares the submitted string directly against the database's `correct_answer`.
3. **Session Integrity & Access Control**:
   - All diagnostic sessions require valid JWT authentication.
   - Users can only take, view, and submit assessments for courses they own.
   - Submissions containing question IDs from other sessions or duplicate entries are rejected (HTTP 400).
   - Once marked `completed`, duplicate submissions are rejected (HTTP 400).

---

## 3. Database Models & Schema Linkage

### `DiagnosticSession` (`diagnostic_sessions`)
| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Unique assessment session identifier |
| `user_id` | UUID (FK -> `users.id`) | Student taking the assessment |
| `course_id` | UUID (FK -> `courses.id`) | Course being evaluated |
| `mode` | String(50) | Assessment mode (`full` or `selected`) |
| `status` | String(50) | Lifecycle state (`in_progress`, `completed`, `abandoned`) |
| `total_questions` | Integer | Total number of questions assigned |
| `correct_answers` | Integer | Number of questions answered correctly |
| `score` | Float | Final score percentage ($0.0 \le \text{score} \le 100.0$) |
| `started_at` | DateTime (UTC) | Session start timestamp |
| `completed_at` | DateTime (UTC) | Session completion timestamp |
| `created_at` | DateTime (UTC) | Record creation timestamp |

### `DiagnosticSessionQuestion` (`diagnostic_session_questions`)
Associates specific questions with a diagnostic session and establishes fixed presentation ordering (`order`).

### `Question` (`questions`)
Stores question prompts, 4 options in JSONB format, the correct answer, educational explanation, difficulty (`easy`, `medium`, `hard`), and origin source (`ai_generated`, `sample/test`, `manually_created`).

### `Attempt` (`attempts`)
Stores individual question attempts with `diagnostic_session_id`, `selected_answer`, server-verified `is_correct` boolean, and `time_taken` in seconds.

---

## 4. Assessment Analytics & Formulas

- **Overall Diagnostic Score**:
  $$\text{Score} = \text{round}\left(\frac{\text{Correct Answers}}{\text{Total Questions}} \times 100.0, 1\right)$$
- **Mastery Status Thresholds**:
  - **Strong**: $\ge 75.0\%$ accuracy
  - **Moderate**: $50.0\% \le \text{accuracy} < 75.0\%$
  - **Weak**: $< 50.0\%$ accuracy
  - **Not Assessed**: 0 questions attempted

---

## 5. API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/courses/{course_id}/diagnostic/start` | Initiates session and returns sanitized questions |
| `GET` | `/api/v1/diagnostic/{diagnostic_id}/questions` | Retrieves questions for an active session without answers |
| `POST` | `/api/v1/diagnostic/{diagnostic_id}/submit` | Evaluates student answers, persists attempts, returns analytics |
| `GET` | `/api/v1/diagnostic/{diagnostic_id}/result` | Retrieves detailed results, score, chart data, and question review |
| `GET` | `/api/v1/courses/{course_id}/diagnostic/history` | Lists past diagnostic attempts and historical scores |

