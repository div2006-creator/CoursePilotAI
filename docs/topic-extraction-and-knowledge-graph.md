# Part 6: AI Topic Extraction & Knowledge Graph

CoursePilot AI features an automated academic syllabus analyzer and interactive knowledge graph visualizer designed to parse course study materials, extract topic hierarchies, infer prerequisite dependencies, and construct a Directed Acyclic Graph (DAG) for personalized learning recovery.

---

## 1. Architecture & Workflow

```
[Uploaded Syllabus PDF]
          │
          ▼
[Document Chunks in Order]
          │
          ▼
[Ollama Local LLM (qwen2.5:3b)] ──> [Topic Extraction Prompt]
          │
          ▼
[Raw JSON Extraction Output]
          │
          ▼
[Topic Validation & Normalization Service]
   ├── Strip Markdown code blocks & parse JSON
   ├── Normalize topic names & whitespace
   ├── Deduplicate concepts within & across units
   ├── Validate prerequisite references against known topics
   ├── Reject self-prerequisites (A -> A)
   └── Detect & drop cycles (Topological / DFS cycle guard)
          │
          ▼
[PostgreSQL Database Transaction]
   ├── Insert / update root Topics with unit grouping
   ├── Insert / update Subtopics linked via parent_id
   └── Insert directed TopicPrerequisite links (confidence + reason)
          │
          ▼
[Interactive Knowledge Graph & Topic List]
   ├── REST API: /api/v1/courses/{course_id}/topics
   ├── REST API: /api/v1/courses/{course_id}/topic-graph
   └── Cytoscape.js canvas with Dagre hierarchical layout
```

---

## 2. Ollama Local LLM Setup

The topic extraction engine runs locally using Ollama, requiring no external paid APIs or sensitive cloud data transfers.

### Installing and Running Ollama
1. Download and install Ollama from [https://ollama.ai](https://ollama.ai).
2. Start the local server:
   ```bash
   ollama serve
   ```
3. Pull the recommended academic model:
   ```bash
   ollama pull qwen2.5:3b
   ```
   *(Alternative models such as `qwen2.5-coder:7b` or `llama3.2:3b` can also be used by setting `OLLAMA_MODEL` in `.env`)*

### Environment Variables
Configure the following in `backend/.env`:
```ini
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_TIMEOUT_SECONDS=90
```

---

## 3. Prompt Engineering

The system prompt is maintained at:
[`backend/app/agents/prompts/topic_extraction_prompt.txt`](file:///c:/Users/hp/OneDrive/Desktop/CoursePilotAI/backend/app/agents/prompts/topic_extraction_prompt.txt)

Key academic constraints enforced by the prompt:
1. **Faithful Extraction**: Only concepts explicitly present in the syllabus text are extracted; no hallucinations.
2. **Terminology Preservation**: Retains original numbering (e.g., "Unit 1: Linear Data Structures").
3. **Hierarchical Grouping**: Unit -> Topic -> Subtopics.
4. **Source Classification**: Explicit concepts are tagged `source_type: "explicit"` with source page numbers.
5. **Prerequisite Inference**: Academic dependencies with confidence scores (0.0 to 1.0) and explanatory educational reasons.
6. **No Self or Circular Loops**: Prerequisite chains must form a strict DAG.

---

## 4. Topic Validation & Cycle Prevention

The service at [`backend/app/services/topic_validation_service.py`](file:///c:/Users/hp/OneDrive/Desktop/CoursePilotAI/backend/app/services/topic_validation_service.py) guarantees data integrity before anything is committed to the database:

- **Markdown Stripping**: Removes backticks and extraneous prose from LLM completions.
- **Deduplication**: Merges topic aliases, subtopics, and page citations across units.
- **Reference Integrity**: Rejects prerequisite edges referring to non-existent topics.
- **Self-Loop Check**: Blocks `prerequisite_id == topic_id`.
- **Cycle Guard**: Evaluates directed edges using depth-first search (DFS) with recursion state tracking; if adding an edge would close a cycle, it is safely dropped.
- **Database Level Protection**: The `TopicPrerequisite` model enforces `before_flush` graph validation and database check constraints.

---

## 5. Knowledge Graph Representation

The service at [`backend/app/services/knowledge_graph_service.py`](file:///c:/Users/hp/OneDrive/Desktop/CoursePilotAI/backend/app/services/knowledge_graph_service.py) constructs nodes and directed edges:

### Edge Semantics
Edge direction is strictly **Foundational Prerequisite $\rightarrow$ Dependent Topic**:
$$\text{Recursion} \longrightarrow \text{Dynamic Programming}$$
```json
{
  "source": "recursion-topic-uuid",
  "target": "dp-topic-uuid",
  "relationship": "prerequisite",
  "confidence": 0.95,
  "reason": "Understanding recursion and call stack state transitions is essential for formulating DP recurrence relations."
}
```

---

## 6. API Endpoints

All endpoints require JWT Bearer Authentication and enforce user-level course ownership.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/courses/{course_id}/extract-topics` | Triggers LLM extraction from course documents and persists DAG |
| `GET` | `/api/v1/courses/{course_id}/topics` | Lists all topics grouped by unit with subtopics |
| `GET` | `/api/v1/courses/{course_id}/topic-graph` | Returns Cytoscape-compatible nodes and directed edges |
| `GET` | `/api/v1/topics/{topic_id}` | Detailed topic view with prerequisites and dependents |
| `PATCH` | `/api/v1/topics/{topic_id}` | Updates topic name, description, difficulty, or unit |
| `DELETE` | `/api/v1/topics/{topic_id}` | Deletes topic and cleans up associated prerequisite links |

---

## 7. Frontend Features

- **Course Details Page** ([`CourseDetails.tsx`](file:///c:/Users/hp/OneDrive/Desktop/CoursePilotAI/frontend/src/pages/CourseDetails.tsx)): Live Topics card with unit/topic counts, status badge, "Extract Topics with AI" button, and links to the breakdown and graph.
- **Topics Breakdown Page** ([`Topics.tsx`](file:///c:/Users/hp/OneDrive/Desktop/CoursePilotAI/frontend/src/pages/Topics.tsx)): Accordion cards grouped by unit, search filtering, difficulty badges (Easy/Medium/Hard), subtopics tags, Edit Topic modal, and Delete confirmation.
- **Knowledge Graph Page** ([`KnowledgeGraph.tsx`](file:///c:/Users/hp/OneDrive/Desktop/CoursePilotAI/frontend/src/pages/KnowledgeGraph.tsx)):
  - Cytoscape.js canvas powered by Dagre hierarchical layout.
  - Color-coded node badges.
  - Interactive zoom, pan, fit-to-screen, and reset controls.
  - Node selection side drawer showing prerequisite chains, unlocked topics, and quick edit.

---

## 8. Running Automated Tests

The test suite runs against an isolated SQLite test database with mocked LLM outputs (Ollama is not required to run automated tests):

```powershell
# Run Part 6 tests
.\backend\.venv\Scripts\python.exe -m pytest backend/app/tests/test_topics.py -v

# Run entire backend test suite (55 tests)
.\backend\.venv\Scripts\python.exe -m pytest backend/app/tests -v

# Run frontend TypeScript & bundle verification
npm run build --prefix frontend
```

---

## 9. Current Limitations & Next Steps

- **Scanned Image PDFs**: If an uploaded PDF contains scanned images without digital text, text extraction flags OCR requirement.
- **Subsequent Parts**: Embeddings, semantic search, diagnostic quizzes, and AI tutor features will be layered on top of this topic graph in Parts 7+.

