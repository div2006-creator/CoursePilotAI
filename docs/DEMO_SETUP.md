# CoursePilot AI — Hackathon Demonstration & Deployment Guide

> **Hackathon Track**: Homingo Hackathon 2026 — Track C3: *A Tutor for Every Learner*  
> **Repository Root**: `CoursePilotAI/`

---

## 1. System Requirements & Prerequisites

| Component | Minimum Version | Recommended Version | Purpose |
|:---|:---|:---|:---|
| **Python** | 3.11+ | 3.12 / 3.14 | Backend API engine & deterministic algorithms |
| **Node.js** | 18.0+ | 20.x LTS | React / TypeScript frontend |
| **PostgreSQL** | 15+ with pgvector | 16 with pgvector 0.7+ | Relational storage & vector chunk retrieval |
| **Ollama** | 0.3.0+ | Latest | Local LLM inference (`llama3.2` / `mistral`) |
| **Docker** | 24+ (Optional) | Latest | One-click containerized deployment |

---

## 2. Quickstart with Demo Seeding (3 Minutes)

CoursePilot AI includes a deterministic zero-friction seeding script that builds an authentic, end-to-end Data Structures & Algorithms learning journey.

### Step 2.1: Start Local Ollama (AI Engine)
Ensure Ollama is running and has the default model pulled:
```bash
# Pull recommended lightweight model (3B parameters, high speed)
ollama pull llama3.2

# Verify Ollama is serving on port 11434
curl http://localhost:11434/api/tags
```
*(Note: If Ollama is offline during evaluation, CoursePilot AI's resilient fallback layer automatically produces deterministic conceptual questions and explanations without crashing!)*

### Step 2.2: Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head
```

### Step 2.3: Seed Authentic Demo Experience
Run the demo seeding engine from repository root:
```bash
# Windows
backend\.venv\Scripts\python scripts\seed_demo.py

# Linux / macOS
backend/.venv/bin/python scripts/seed_demo.py
# or execute bash wrapper:
bash scripts/setup_demo.sh
```

**What the Seed Engine Establishes Automatically:**
1. **User Account**: `demo@coursepilot.ai` / `DemoStudent2026!`
2. **Course**: *Data Structures & Algorithms (CS201) [DEMO]*
3. **Curriculum**: 14 topics across 4 Units with 13 DAG prerequisite edges.
4. **Syllabus Document**: 14-page PDF indexed with 48 text chunks and pgvector embeddings.
5. **Baseline Diagnostic**: Assessment record identifying student struggling on *DP State* (20% accuracy) blocking *Tabulation* and *Grid DP*.
6. **Adaptive Study Plan**: Personalized 14-day calendar prioritizing foundational blockers.
7. **AI Tutor Session**: Multi-turn Hinglish dialogue on *DP State* with citations and Socratic guidance.
8. **Fresh Post-Tutoring Practice**: 4 newly answered verification questions proving a **+65 percentage point** observable learning improvement (20% $\rightarrow$ 85% mastery).

---

## 3. Running Frontend & Backend on Localhost

### Backend Startup:
```bash
cd backend
# With virtual environment active:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be immediately available at:
- Swagger UI: `http://localhost:8000/docs`
- Redoc: `http://localhost:8000/redoc`
- Deep Health Check: `http://localhost:8000/api/v1/health`

### Frontend Startup:
```bash
cd frontend
npm install
npm run dev
```
Open your browser at `http://localhost:5173`.

---

## 4. Resetting Demo State Between Presentations

To re-run the demo from scratch or clear all demo account artifacts without affecting other users:
```bash
# Reset demo data cleanly:
backend\.venv\Scripts\python scripts\reset_demo.py

# Re-seed fresh demo data:
backend\.venv\Scripts\python scripts\seed_demo.py
```

---

## 5. Docker Compose Deployment (Alternative)

For a fully isolated containerized environment:
```bash
# Start PostgreSQL (with pgvector), Backend, and Frontend
docker compose up -d

# Check service logs
docker compose logs -f backend
```

---

## 6. Demo User Credentials Summary

| Credential | Value |
|:---|:---|
| **URL** | `http://localhost:5173` |
| **Email** | `demo@coursepilot.ai` |
| **Password** | `DemoStudent2026!` |
| **Pre-loaded Course** | *Data Structures & Algorithms (CS201) [DEMO]* |
| **Key Demo Story** | Student unlocks bottleneck on *DP State*, advancing from 20% to 85% mastery! |

