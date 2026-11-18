# CoursePilot AI — REST API Documentation

This document outlines the planned API specifications for CoursePilot AI backend services.

**Base URL**: `/api/v1`

---

## 1. System & Health

### `GET /api/v1/health`
Checks backend and service availability.

- **Response `200 OK`**:
```json
{
  "status": "healthy",
  "app_name": "CoursePilot AI API",
  "version": "0.1.0",
  "timestamp": "2026-11-17T14:45:00Z",
  "database": "connected"
}
```

---

## 2. Authentication & User Profile (Planned)

### `POST /api/v1/auth/register`
Create a new student account.
- **Request Body**: `{ "email": "student@example.com", "password": "securepassword", "full_name": "Jane Doe" }`
- **Response `201 Created`**: User profile object and JWT bearer access token.

### `POST /api/v1/auth/login`
Authenticate with email and password.
- **Request Body**: `{ "username": "student@example.com", "password": "securepassword" }` (OAuth2 compatible form)
- **Response `200 OK`**: `{ "access_token": "...", "token_type": "bearer" }`

### `GET /api/v1/auth/me`
Retrieve authenticated student's profile.
- **Headers**: `Authorization: Bearer <token>`
- **Response `200 OK`**: Student user details and active course enrollments.

---

## 3. Courses & Syllabus Ingestion (Planned)

### `POST /api/v1/courses/upload-syllabus`
Upload a PDF syllabus file for automated topic and prerequisite extraction.
- **Content-Type**: `multipart/form-data`
- **Form Data**: `file: <binary_pdf>`, `course_code: "CS201"`, `title: "Data Structures & Algorithms"`
- **Response `202 Accepted`**: Ingestion job identifier and extracted preliminary topic summary.

### `GET /api/v1/courses`
List enrolled or uploaded courses.

### `GET /api/v1/courses/{course_id}/topics`
Get the structured topic hierarchy and prerequisite relationships.
- **Response `200 OK`**:
```json
{
  "course_id": "c100",
  "topics": [
    {
      "id": "top_01",
      "name": "Asymptotic Analysis",
      "prerequisites": []
    },
    {
      "id": "top_02",
      "name": "Arrays & Strings",
      "prerequisites": ["top_01"]
    }
  ]
}
```

---

## 4. Diagnostic Assessment & Gap Analysis (Planned)

### `POST /api/v1/assessments/diagnostic/generate`
Generate an adaptive diagnostic quiz based on course topics.
- **Request Body**: `{ "course_id": "c100", "question_count": 10 }`
- **Response `200 OK`**: Quiz payload with question items (without revealed answers).

### `POST /api/v1/assessments/diagnostic/submit`
Submit student answers to evaluate mastery and detect prerequisite gaps.
- **Request Body**:
```json
{
  "assessment_id": "a200",
  "answers": [
    { "question_id": "q_01", "selected_option": "O(log N)" }
  ]
}
```
- **Response `200 OK`**:
```json
{
  "score": 0.70,
  "weak_topics": ["top_05_recursion_backtracking"],
  "mastery_updates": {
    "top_01_asymptotic_analysis": 0.90,
    "top_05_recursion_backtracking": 0.40
  }
}
```

---

## 5. Personalized Study Plan (Planned)

### `POST /api/v1/plans/generate`
Generate a step-by-step recovery study plan based on diagnostic gaps and target exam date.
- **Request Body**: `{ "course_id": "c100", "target_date": "2026-12-15", "daily_hours": 2 }`
- **Response `201 Created`**: Detailed milestone plan with recommended readings, tasks, and practice exercises.

### `GET /api/v1/plans/active`
Retrieve the current active study plan and task completion status.

---

## 6. AI Tutor & RAG Chat (Planned)

### `POST /api/v1/tutor/chat`
Ask the AI Tutor a question with context grounding from uploaded materials.
- **Request Body**:
```json
{
  "course_id": "c100",
  "topic_id": "top_03_linked_lists",
  "message": "Why does Floyd's cycle detection algorithm use slow and fast pointers instead of two slow pointers?",
  "session_id": "s300"
}
```
- **Response `200 OK`**:
```json
{
  "reply": "Floyd's algorithm uses pointers moving at different speeds (1 step and 2 steps)...",
  "citations": [
    {
      "source_document": "CS201_Lecture3_LinkedLists.pdf",
      "page": 14,
      "snippet": "Floyd's cycle-finding algorithm..."
    }
  ]
}
```

---

## 7. Analytics (Planned)

### `GET /api/v1/analytics/mastery`
Aggregated mastery metrics across all syllabus topics for charting.

