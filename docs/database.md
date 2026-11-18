# CoursePilot AI — Database Architecture & Schema Reference

CoursePilot AI uses **PostgreSQL 16+** with the **pgvector** extension, managed via **SQLAlchemy 2.0** and **Alembic** migrations.

---

## 1. Entity-Relationship Overview

```mermaid
erDiagram
    users ||--o{ courses : "owns"
    users ||--o{ attempts : "submits"
    users ||--o{ topic_mastery : "tracks"
    users ||--o{ study_plans : "receives"
    users ||--o{ agent_runs : "triggers"

    courses ||--o{ documents : "contains"
    courses ||--o{ topics : "organizes"
    courses ||--o{ attempts : "scopes"
    courses ||--o{ study_plans : "targets"

    documents ||--o{ document_chunks : "splits into"

    topics ||--o{ topics : "parent_id"
    topics ||--o{ topic_prerequisites : "requires"
    topics ||--o{ questions : "assessed by"
    topics ||--o{ attempts : "measured in"
    topics ||--o{ topic_mastery : "mastered via"
    topics ||--o{ plan_items : "scheduled in"

    questions ||--o{ attempts : "answered by"
    study_plans ||--o{ plan_items : "contains"
```

---

## 2. Core Design Conventions

- **Primary Keys**: All entity tables use `UUID` primary keys (`uuid.uuid4`), except the `topic_prerequisites` join table which uses a composite primary key `(topic_id, prerequisite_id)`.
- **Timestamps**: All timestamp columns use timezone-aware UTC (`TIMESTAMP WITH TIME ZONE` / `DateTime(timezone=True)`).
- **Vector Search**: `document_chunks.embedding` uses `pgvector` `VECTOR(384)` (aligned with `sentence-transformers/all-MiniLM-L6-v2`).
- **Cascading Deletes**: Child records use `ON DELETE CASCADE` (`topics.parent_id` uses `ON DELETE SET NULL`) so removing a user, course, document, topic, or study plan cleans up dependent records consistently.
- **Deterministic Naming**: All constraints and indexes follow SQLAlchemy naming conventions (`pk_`, `fk_`, `uq_`, `ck_`, `ix_`) for predictable Alembic autogeneration.

---

## 3. Table Reference

### 3.1 `users` (`backend/app/models/user.py`)
**Purpose**: Stores registered learner accounts and credentials.

| Column | Type | Constraints / Indexes | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | **PK** | Unique user identifier |
| `name` | `VARCHAR(255)` | `NOT NULL` | Display name |
| `email` | `VARCHAR(255)` | `NOT NULL`, **UNIQUE**, Indexed | Unique login email |
| `password_hash` | `VARCHAR(255)` | `NOT NULL` | Hashed password credential |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, `DEFAULT now()` | Account creation UTC timestamp |

**Relationships**: One-to-many with `courses`, `attempts`, `topic_mastery`, `study_plans`, and `agent_runs`.

---

### 3.2 `courses` (`backend/app/models/course.py`)
**Purpose**: Represents a learner's course workspace, exam target date, and daily study budget.

| Column | Type | Constraints / Indexes | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | **PK** | Unique course identifier |
| `user_id` | `UUID` | **FK** $\rightarrow$ `users.id` (`CASCADE`), Indexed | Course owner |
| `title` | `VARCHAR(255)` | `NOT NULL` | Course title (e.g., Data Structures & Algorithms) |
| `description` | `TEXT` | Nullable | Optional course overview |
| `exam_date` | `DATE` | Nullable, Indexed | Target exam date for recovery scheduling |
| `daily_minutes` | `INTEGER` | `NOT NULL`, `DEFAULT 60`, `CHECK (> 0)` | Available study time per day |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, `DEFAULT now()` | Creation UTC timestamp |

**Relationships**: Many-to-one with `users`; one-to-many with `documents`, `topics`, `attempts`, and `study_plans`.

---

### 3.3 `documents` (`backend/app/models/document.py`)
**Purpose**: Tracks uploaded syllabus PDFs, lecture notes, and ingestion status.

| Column | Type | Constraints / Indexes | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | **PK** | Unique document identifier |
| `course_id` | `UUID` | **FK** $\rightarrow$ `courses.id` (`CASCADE`), Indexed | Owning course |
| `filename` | `VARCHAR(255)` | `NOT NULL` | Original uploaded file name |
| `file_path` | `VARCHAR(1024)` | `NOT NULL` | Storage path |
| `status` | `VARCHAR(50)` | `NOT NULL`, `DEFAULT 'pending'`, Indexed | Processing state (`pending`, `processed`, `failed`) |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, `DEFAULT now()` | Upload UTC timestamp |

**Composite Indexes**: `(course_id, status)`.  
**Relationships**: Many-to-one with `courses`; one-to-many with `document_chunks`.

---

### 3.4 `document_chunks` (`backend/app/models/document_chunk.py`)
**Purpose**: Stores extracted text segments and 384-dimensional vector embeddings for pgvector RAG retrieval.

| Column | Type | Constraints / Indexes | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | **PK** | Unique chunk identifier |
| `document_id` | `UUID` | **FK** $\rightarrow$ `documents.id` (`CASCADE`), Indexed | Source document |
| `content` | `TEXT` | `NOT NULL` | Extracted text segment |
| `page_number` | `INTEGER` | Nullable, `CHECK (page_number >= 1)` | Source PDF page number |
| `embedding` | `VECTOR(384)` | Nullable | Dense embedding vector for cosine/L2 similarity search |

**Composite Indexes**: `(document_id, page_number)`.  
**Relationships**: Many-to-one with `documents`.

---

### 3.5 `topics` (`backend/app/models/topic.py`)
**Purpose**: Represents syllabus concepts and optional parent/subtopic hierarchies within a course.

| Column | Type | Constraints / Indexes | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | **PK** | Unique topic identifier |
| `course_id` | `UUID` | **FK** $\rightarrow$ `courses.id` (`CASCADE`), Indexed | Owning course |
| `name` | `VARCHAR(255)` | `NOT NULL`, Indexed | Concept/topic name |
| `description` | `TEXT` | Nullable | Topic learning objectives or summary |
| `difficulty` | `VARCHAR(50)` | `NOT NULL`, `DEFAULT 'beginner'`, Indexed | Difficulty tier (`beginner`, `intermediate`, `advanced`) |
| `parent_id` | `UUID` | **FK** $\rightarrow$ `topics.id` (`SET NULL`), Nullable, Indexed | Optional parent topic (`CHECK (parent_id IS NULL OR parent_id <> id)`) |

**Composite Indexes**: `(course_id, name)`, `(course_id, difficulty)`.  
**Relationships**: Many-to-one with `courses`; self-referential `parent`/`subtopics`; many-to-many `prerequisites`/`dependents` via `topic_prerequisites`; one-to-many with `questions`, `attempts`, `topic_mastery`, and `plan_items`.

---

### 3.6 `topic_prerequisites` (`backend/app/models/topic_prerequisite.py`)
**Purpose**: Models directed prerequisite relationships (`topic_id` requires `prerequisite_id`) forming a Directed Acyclic Graph (DAG).

| Column | Type | Constraints / Indexes | Description |
| :--- | :--- | :--- | :--- |
| `topic_id` | `UUID` | **PK**, **FK** $\rightarrow$ `topics.id` (`CASCADE`) | Dependent topic |
| `prerequisite_id` | `UUID` | **PK**, **FK** $\rightarrow$ `topics.id` (`CASCADE`), Indexed | Required foundational topic |

**Integrity & Cycle Prevention**:
- **Database Constraint**: `CHECK (topic_id <> prerequisite_id)` prevents self-referencing prerequisites.
- **ORM Flush Guard**: A SQLAlchemy `before_flush` listener (`_prevent_circular_prerequisites`) and `validate_no_prerequisite_cycle()` traverse existing and pending edges to reject circular prerequisite chains (e.g., $A \rightarrow B \rightarrow A$ or $A \rightarrow B \rightarrow C \rightarrow A$) with `CircularPrerequisiteError`.

---

### 3.7 `questions` (`backend/app/models/question.py`)
**Purpose**: Question bank for diagnostic quizzes and concept checks.

| Column | Type | Constraints / Indexes | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | **PK** | Unique question identifier |
| `topic_id` | `UUID` | **FK** $\rightarrow$ `topics.id` (`CASCADE`), Indexed | Assessed topic |
| `question` | `TEXT` | `NOT NULL` | Question prompt |
| `options` | `JSONB` | `NOT NULL` | Answer options payload |
| `correct_answer` | `TEXT` | `NOT NULL` | Canonical correct option/answer |
| `explanation` | `TEXT` | Nullable | Detailed solution explanation |
| `difficulty` | `VARCHAR(50)` | `NOT NULL`, `DEFAULT 'medium'`, Indexed | Difficulty level |
| `source` | `VARCHAR(100)` | `NOT NULL`, `DEFAULT 'seed'`, Indexed | Origin (`seed`, `syllabus_generated`, etc.) |

**Composite Indexes**: `(topic_id, difficulty)`.  
**Relationships**: Many-to-one with `topics`; one-to-many with `attempts`.

---

### 3.8 `attempts` (`backend/app/models/attempt.py`)
**Purpose**: Immutable log of every learner answer submitted during diagnostics and practice.

| Column | Type | Constraints / Indexes | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | **PK** | Unique attempt identifier |
| `user_id` | `UUID` | **FK** $\rightarrow$ `users.id` (`CASCADE`), Indexed | Submitting learner |
| `course_id` | `UUID` | **FK** $\rightarrow$ `courses.id` (`CASCADE`), Indexed | Course context |
| `topic_id` | `UUID` | **FK** $\rightarrow$ `topics.id` (`CASCADE`), Indexed | Topic evaluated |
| `question_id` | `UUID` | **FK** $\rightarrow$ `questions.id` (`CASCADE`), Indexed | Question answered |
| `selected_answer` | `TEXT` | `NOT NULL` | Learner's submitted answer |
| `is_correct` | `BOOLEAN` | `NOT NULL`, Indexed | Correctness flag |
| `time_taken` | `INTEGER` | `NOT NULL`, `DEFAULT 0`, `CHECK (>= 0)` | Response duration in seconds |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, `DEFAULT now()`, Indexed | Submission UTC timestamp |

**Composite Indexes**: `(user_id, course_id)`, `(user_id, topic_id)`.

---

### 3.9 `topic_mastery` (`backend/app/models/topic_mastery.py`)
**Purpose**: Tracks the latest estimated mastery and confidence scores for each `(user, topic)` pair.

| Column | Type | Constraints / Indexes | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | **PK** | Unique record identifier |
| `user_id` | `UUID` | **FK** $\rightarrow$ `users.id` (`CASCADE`), Indexed | Learner |
| `topic_id` | `UUID` | **FK** $\rightarrow$ `topics.id` (`CASCADE`), Indexed | Evaluated topic |
| `mastery_score` | `DOUBLE PRECISION` | `NOT NULL`, `DEFAULT 0.0`, `CHECK (0.0..1.0)` | Estimated concept mastery |
| `confidence_score` | `DOUBLE PRECISION` | `NOT NULL`, `DEFAULT 0.0`, `CHECK (0.0..1.0)` | Estimation confidence |
| `last_assessed_at` | `TIMESTAMPTZ` | Nullable | Last mastery update UTC timestamp |

**Unique Constraint**: `uq_topic_mastery_user_topic` on `(user_id, topic_id)` prevents duplicate mastery records.

---

### 3.10 `study_plans` (`backend/app/models/study_plan.py`)
**Purpose**: Versioned container for personalized recovery study roadmaps.

| Column | Type | Constraints / Indexes | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | **PK** | Unique plan identifier |
| `user_id` | `UUID` | **FK** $\rightarrow$ `users.id` (`CASCADE`), Indexed | Target learner |
| `course_id` | `UUID` | **FK** $\rightarrow$ `courses.id` (`CASCADE`), Indexed | Target course |
| `version` | `INTEGER` | `NOT NULL`, `DEFAULT 1`, `CHECK (>= 1)` | Plan revision number |
| `status` | `VARCHAR(50)` | `NOT NULL`, `DEFAULT 'active'`, Indexed | Lifecycle status (`active`, `archived`, `completed`) |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, `DEFAULT now()` | Generation UTC timestamp |

**Composite Indexes**: `(user_id, course_id, status)`.  
**Relationships**: Many-to-one with `users` and `courses`; one-to-many with `plan_items`.

---

### 3.11 `plan_items` (`backend/app/models/plan_item.py`)
**Purpose**: Individual dated study tasks within a `study_plans` version.

| Column | Type | Constraints / Indexes | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | **PK** | Unique item identifier |
| `plan_id` | `UUID` | **FK** $\rightarrow$ `study_plans.id` (`CASCADE`), Indexed | Parent study plan |
| `topic_id` | `UUID` | **FK** $\rightarrow$ `topics.id` (`CASCADE`), Indexed | Topic to study |
| `scheduled_date` | `DATE` | `NOT NULL`, Indexed | Planned study date |
| `duration_minutes` | `INTEGER` | `NOT NULL`, `CHECK (> 0)` | Allocated duration in minutes |
| `priority` | `INTEGER` | `NOT NULL`, `DEFAULT 1`, `CHECK (>= 1)` | Scheduling priority rank |
| `status` | `VARCHAR(50)` | `NOT NULL`, `DEFAULT 'pending'`, Indexed | Task progress (`pending`, `in_progress`, `completed`, `skipped`) |

**Composite Indexes**: `(plan_id, scheduled_date)`.

---

### 3.12 `agent_runs` (`backend/app/models/agent_run.py`)
**Purpose**: Structured audit and observability log for AI agent invocations.

| Column | Type | Constraints / Indexes | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | **PK** | Unique execution identifier |
| `user_id` | `UUID` | **FK** $\rightarrow$ `users.id` (`CASCADE`), Indexed | Triggering learner |
| `task_type` | `VARCHAR(100)` | `NOT NULL`, Indexed | Workflow type (e.g., `syllabus_parse`, `plan_generate`, `tutor_chat`) |
| `status` | `VARCHAR(50)` | `NOT NULL`, `DEFAULT 'pending'`, Indexed | Execution state (`pending`, `running`, `completed`, `failed`) |
| `input_data` | `JSONB` | `NOT NULL` | Structured agent input payload |
| `output_data` | `JSONB` | Nullable | Structured agent output payload |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, `DEFAULT now()`, Indexed | Execution start UTC timestamp |

**Composite Indexes**: `(user_id, task_type, created_at)`.

---

## 4. Running Database Migrations (Alembic)

Alembic is configured via [alembic.ini](file:///c:/Users/hp/OneDrive/Desktop/CoursePilotAI/backend/alembic.ini) and [env.py](file:///c:/Users/hp/OneDrive/Desktop/CoursePilotAI/database/migrations/env.py), pulling `DATABASE_URL` automatically from `.env` via `app.config.settings`.

> **Important**: Never use `Base.metadata.create_all()` in production. Always apply schema changes through Alembic migrations.

### Step 1: Start PostgreSQL with `pgvector`
Recommended via Docker Compose (includes `pgvector/pgvector:pg16`):
```bash
docker-compose up -d
```

Or configure `DATABASE_URL` in `.env` pointing to a PostgreSQL 16+ database with the `pgvector` extension installed:
```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/coursepilot
```

### Step 2: Apply Migrations
From the `backend/` directory (with virtual environment activated):
```bash
cd backend
alembic upgrade head
```

Or from the project root:
```bash
alembic -c backend/alembic.ini upgrade head
```

### Step 3: Common Alembic Commands
```bash
# View current applied revision
alembic -c backend/alembic.ini current

# View migration history
alembic -c backend/alembic.ini history

# Preview SQL without executing against the database
alembic -c backend/alembic.ini upgrade head --sql

# Auto-generate a new migration after editing ORM models
alembic -c backend/alembic.ini revision --autogenerate -m "describe_change"

# Roll back the most recent migration
alembic -c backend/alembic.ini downgrade -1
```

