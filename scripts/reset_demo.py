"""CoursePilot AI - Demo Data Cleanup Script.

Removes all synthetic records associated with demo@coursepilot.ai.
Preserves all regular user accounts and real data.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend app is on sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.user import User

DEMO_USER_EMAIL = "demo@coursepilot.ai"


def reset_demo() -> None:
    db: Session = SessionLocal()
    try:
        user = db.execute(select(User).where(User.email == DEMO_USER_EMAIL)).scalar_one_or_none()
        if not user:
            print(f"[!] No demo user found with email {DEMO_USER_EMAIL}. Nothing to clean.")
            return

        print(f"[*] Deleting demo user: {DEMO_USER_EMAIL} (ID: {user.id})...")
        # Cascades in PostgreSQL handle Course, Documents, Topics, Attempts, TutorSessions, Plans
        db.delete(user)
        db.commit()
        print("[+] Demo user and all associated demo data deleted successfully.")
    except Exception as exc:
        db.rollback()
        print(f"[-] Error resetting demo data: {exc}")
    finally:
        db.close()


if __name__ == "__main__":
    reset_demo()

