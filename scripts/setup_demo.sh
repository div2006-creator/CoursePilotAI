#!/usr/bin/env bash
# =============================================================================
# CoursePilot AI - Demo Environment Setup Script
# Homingo Hackathon 2026 (Track C3 - A Tutor for Every Learner)
# =============================================================================
set -e

echo "================================================================="
echo " CoursePilot AI — Hackathon 2026 Demo Environment Setup"
echo "================================================================="

# 1. Check Python virtual environment
if [ -d "backend/.venv" ]; then
    echo "[*] Using backend virtual environment..."
    PYTHON_BIN="backend/.venv/bin/python"
    ALEMBIC_BIN="backend/.venv/bin/alembic"
    if [ ! -f "$PYTHON_BIN" ]; then
        PYTHON_BIN="backend/.venv/Scripts/python.exe"
        ALEMBIC_BIN="backend/.venv/Scripts/alembic.exe"
    fi
else
    echo "[*] Using system python..."
    PYTHON_BIN="python"
    ALEMBIC_BIN="alembic"
fi

# 2. Apply Database Migrations
echo "[*] Applying database migrations to latest head..."
"$ALEMBIC_BIN" -c backend/alembic.ini upgrade head

# 3. Seed Synthetic Educational Scenario
echo "[*] Seeding reproducible DSA demo curriculum and student scenario..."
"$PYTHON_BIN" scripts/seed_demo.py

echo ""
echo "================================================================="
echo " SETUP COMPLETED SUCCESSFULLY!"
echo "================================================================="
echo " Demo Login Credentials:"
echo "   Email:    demo@coursepilot.ai"
echo "   Password: DemoStudent2026!"
echo ""
echo " Start Backend (Terminal 1):"
echo "   cd backend && uvicorn app.main:app --reload --port 8000"
echo ""
echo " Start Frontend (Terminal 2):"
echo "   cd frontend && npm run dev"
echo ""
echo " Open in Browser: http://localhost:5173"
echo "================================================================="

