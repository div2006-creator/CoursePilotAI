# CoursePilot AI 🚀

> **AI-Powered Personalized Learning Recovery Platform for Data Structures & Algorithms (DSA)**

CoursePilot AI analyzes computer science course syllabi, extracts concept prerequisite relationships into a dependency graph, pinpoints learning gaps using adaptive diagnostic assessments, generates personalized recovery study plans, and offers a grounded RAG-powered AI tutor.

---

## 📌 Features Overview

- **Syllabus & Course Ingestion**: Parses university course syllabi and lecture slides (PDFs) to extract hierarchical topics and learning objectives.
- **Prerequisite Knowledge Graph**: Maps topics into a Directed Acyclic Graph (DAG) capturing dependency chains (e.g., Recursion $\rightarrow$ Trees $\rightarrow$ Graphs $\rightarrow$ Dynamic Programming).
- **Diagnostic Gap Identification**: Generates adaptive diagnostic quizzes to identify prerequisite deficiencies and calibrate topic mastery.
- **Knowledge Gap Analysis & Prerequisite Intelligence**: Graph traversal distinguishing root prerequisite failures from isolated topic struggles.
- **Adaptive Learning Planner**: Synthesizes time-bound, prerequisite-respecting study roadmaps prioritizing foundational gaps before advanced topics, with dynamic replanning and rolling exam schedules (see [Learning Planner](docs/LEARNING_PLANNER.md)).
- **Personalized AI Tutor**: 1-on-1 pedagogical tutor guided by a Socratic state machine (`DIAGNOSIS` $\rightarrow$ `EXPLANATION` $\rightarrow$ `EXAMPLE` $\rightarrow$ `PRACTICE` $\rightarrow$ `VERIFICATION` $\rightarrow$ `COMPLETED`), grounded in uploaded syllabus chunks with exact citations (`Source: Unit 3, Page 12`), multi-language explanations (`English`, `Hindi`, `Hinglish`), progressive hints, and deterministic mastery updates (see [AI Tutor](docs/AI_TUTOR.md)).
- **Learning Analytics & Adaptive Progress Intelligence**: 100% deterministic, explainable progress tracking that compares initial diagnostic baselines against *fresh* assessment attempts (strictly excluding duplicate questions to verify true concept retention), tracks longitudinal mastery velocity and milestone graduations, computes a transparent 5-component Exam Readiness Score with a 40% coverage reliability threshold, calculates honest calendar-day streaks, and detects foundational prerequisite bottlenecks (see [Learning Analytics](docs/LEARNING_ANALYTICS.md)).

---

## 🛠️ Technology Stack

### Frontend
- **Framework**: [React 18](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/)
- **Bundler & Tooling**: [Vite](https://vitejs.dev/)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/)
- **Routing**: [React Router](https://reactrouter.com/)
- **Charts & Visualizations**: [Recharts](https://recharts.org/)
- **Icons**: [Lucide React](https://lucide.dev/)
- **HTTP Client**: [Axios](https://axios-http.com/)

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous Python Web Framework)
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org/)
- **ORM & DB Toolkit**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
- **Validation & Settings**: [Pydantic v2](https://docs.pydantic.dev/) + [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **Database Driver**: [psycopg 3](https://www.psycopg.org/psycopg3/)
- **Vector Search**: [pgvector](https://github.com/pgvector/pgvector-python)

### AI & Retrieval
- **Local LLM Engine**: [Ollama](https://ollama.ai/) running `qwen2.5-coder` / `qwen2.5`
- **Embeddings**: [Sentence Transformers](https://sbert.net/) (`sentence-transformers/all-MiniLM-L6-v2`)
- **Document Extraction**: [PyMuPDF](https://pymupdf.readthedocs.io/) (`fitz`)

### Database & Infrastructure
- **Database Engine**: PostgreSQL 16 with `pgvector`
- **Containerization**: Docker & Docker Compose

---

## 📁 Repository Structure

```text
coursepilot-ai/
│
├── frontend/                     # React + TypeScript + Vite Client
│   ├── public/                   # Static assets & favicon
│   ├── src/
│   │   ├── assets/               # Visual assets and media
│   │   ├── components/           # Component library
│   │   │   ├── common/           # Common primitives (Navbar, buttons, modals)
│   │   │   ├── dashboard/        # Dashboard overview widgets
│   │   │   ├── course/           # Syllabus and course management
│   │   │   ├── quiz/             # Diagnostic assessment UI
│   │   │   ├── tutor/            # Interactive AI tutor chat interface
│   │   │   └── roadmap/          # Prerequisite graphs & study plans
│   │   ├── pages/                # Route container pages
│   │   ├── services/             # Axios API client services
│   │   ├── hooks/                # Custom React hooks
│   │   ├── context/              # Context providers
│   │   ├── types/                # TypeScript interfaces and models
│   │   ├── utils/                # Frontend helper utilities
│   │   ├── App.tsx               # Root App component and routing
│   │   ├── main.tsx              # React entry point
│   │   └── index.css             # Tailwind base & global CSS
│   ├── index.html                # Vite HTML entry point
│   ├── package.json              # Frontend dependencies and scripts
│   ├── tsconfig.json             # TypeScript compiler configuration
│   └── vite.config.ts            # Vite build and proxy configuration
│
├── backend/                      # FastAPI Application
│   ├── app/
│   │   ├── api/                  # API routers & dependency injection
│   │   │   ├── routes/           # Domain route handlers
│   │   │   └── dependencies.py   # Database session & auth dependencies
│   │   ├── core/                 # Core configs, DB engine, and security
│   │   │   └── database.py       # SQLAlchemy engine & session factory
│   │   ├── models/               # SQLAlchemy ORM models
│   │   ├── schemas/              # Pydantic validation schemas
│   │   ├── services/             # Business domain services
│   │   ├── agents/               # AI Agent orchestration
│   │   │   ├── tools/            # Agent tool definitions
│   │   │   ├── prompts/          # Structured prompt templates
│   │   │   ├── orchestrator.py   # Agent execution orchestrator
│   │   │   └── state.py          # Workflow state representation
│   │   ├── ai/                   # Vector store & Ollama client modules
│   │   ├── tests/                # Pytest automated test suite
│   │   │   └── test_health.py    # Health check tests
│   │   ├── main.py               # FastAPI application factory
│   │   └── config.py             # Environment configuration (Pydantic)
│   ├── requirements.txt          # Python dependencies
│   └── .env.example              # Backend environment variables template
│
├── database/                     # Database scripts & seeds
│   ├── migrations/               # Alembic database migrations
│   ├── seed/                     # Seed datasets for testing
│   │   ├── dsa_topics.json       # Canonical DSA topic syllabus hierarchy
│   │   └── dsa_questions.json    # Diagnostic questions bank
│   └── schema.sql                # Initial schema & pgvector extension setup
│
├── sample_data/                  # Sample syllabi and lecture PDFs
│
├── docs/                         # Technical documentation
│   ├── architecture.md           # System design & architecture details
│   ├── api.md                    # REST API endpoint specifications
│   ├── LEARNING_PLANNER.md       # Adaptive study planner documentation
│   ├── AI_TUTOR.md               # Socratic Personalized AI Tutor documentation
│   └── evaluation.md             # AI evaluation metrics & benchmark plan
│
├── docker-compose.yml            # PostgreSQL 16 + pgvector container config
├── .gitignore                    # Git ignore rules
└── README.md                     # Project documentation
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Node.js**: v18.0.0 or higher
- **npm**: v9.0.0 or higher
- **Python**: v3.11 or higher
- **Docker & Docker Compose** (for PostgreSQL + pgvector)

### 2. Environment Configuration
Copy `.env.example` to `.env` in both the project root and backend:

```bash
# On Linux / macOS
cp .env.example .env
cp backend/.env.example backend/.env

# On Windows (PowerShell)
Copy-Item .env.example .env
Copy-Item backend/.env.example backend/.env
```

---

### 3. Start Database (PostgreSQL + pgvector)
Run the pgvector-enabled PostgreSQL container via Docker Compose:

```bash
docker-compose up -d
```

Verify the database container is running and healthy:
```bash
docker-compose ps
```

---

### 4. Backend Setup & Run

Navigate to the `backend/` directory, activate a virtual environment, and install dependencies:

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify backend health:
- Health check URL: `http://localhost:8000/api/v1/health`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`

Run backend tests:
```bash
pytest
```

---

### 5. Frontend Setup & Run

In a separate terminal, navigate to the `frontend/` directory:

```bash
cd frontend

# Install npm dependencies
npm install

# Start the Vite development server
npm run dev
```

Open your browser to:
- `http://localhost:5173`

The frontend automatically proxies `/api` calls to `http://127.0.0.1:8000`.

---

## 📊 Verification Endpoints

| Endpoint | Method | Purpose | Expected Status |
| :--- | :--- | :--- | :--- |
| `/api/v1/health` | `GET` | System health check | `200 OK` |
| `/` | `GET` | Root API service information | `200 OK` |
| `/docs` | `GET` | Swagger UI documentation | `200 OK` |
| `/redoc` | `GET` | ReDoc API documentation | `200 OK` |

---

## 📄 License
This project is licensed under the MIT License.

