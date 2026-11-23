"""CoursePilot AI - Reproducible Demo Data Seed Script.

Target: Homingo Hackathon 2026 (Track C3 - A Tutor for Every Learner)
Curriculum: Data Structures & Algorithms (CS201)
Scenario:
- Foundational mastery in Arrays, Strings, Recursion (Strong)
- Struggling in Dynamic Programming: DP State (Weak), Tabulation (Weak), Grid DP (Weak), Memoization (Developing)
- Demonstrates how CoursePilot isolates DP State as the foundational bottleneck
- Includes verified fresh post-tutoring assessment records showing observable learning improvement
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import sys
from pathlib import Path
import uuid

# Ensure backend app is on sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, utc_now
from app.core.security import hash_password
from app.models.attempt import Attempt
from app.models.course import Course
from app.models.diagnostic_session import DiagnosticSession
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_gap import KnowledgeGapAnalysis
from app.models.plan_item import PlanItem
from app.models.question import Question
from app.models.study_plan import StudyPlan
from app.models.topic import Topic
from app.models.topic_mastery import TopicMastery
from app.models.topic_mastery_history import TopicMasteryHistory
from app.models.topic_prerequisite import TopicPrerequisite
from app.models.tutor_message import TutorMessage
from app.models.tutor_session import (
    STAGE_COMPLETED,
    STATUS_COMPLETED,
    TutorSession,
)
from app.models.user import User
from app.services.retrieval_service import generate_query_embedding

DEMO_USER_EMAIL = "demo@coursepilot.ai"
DEMO_USER_PASSWORD = "DemoStudent2026!"
DEMO_USER_NAME = "Demo Student (DSA Learner)"


def clean_demo_data(db: Session) -> None:
    """Safely remove previous demo user records without touching other accounts."""
    user = db.execute(select(User).where(User.email == DEMO_USER_EMAIL)).scalar_one_or_none()
    if user:
        print(f"[*] Removing existing demo data for {DEMO_USER_EMAIL}...")
        db.delete(user)
        db.commit()
        print("[+] Existing demo data cleaned successfully.")


def seed_demo() -> None:
    db: Session = SessionLocal()
    try:
        clean_demo_data(db)

        now = utc_now()
        three_days_ago = now - timedelta(days=3)
        yesterday = now - timedelta(days=1)
        exam_date = date.today() + timedelta(days=14)

        print(f"[*] Creating demo user: {DEMO_USER_EMAIL}...")
        demo_user = User(
            email=DEMO_USER_EMAIL,
            password_hash=hash_password(DEMO_USER_PASSWORD),
            name=DEMO_USER_NAME,
            created_at=three_days_ago,
        )
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)

        # 1. Create Course
        print("[*] Creating course: Data Structures & Algorithms (CS201) [DEMO]...")
        course = Course(
            user_id=demo_user.id,
            title="Data Structures & Algorithms (CS201) [DEMO]",
            description="Core Computer Science Curriculum covering Foundations, Dynamic Programming, Trees, and Graphs.",
            exam_date=exam_date,
            daily_minutes=45,
            created_at=three_days_ago,
        )
        db.add(course)
        db.commit()
        db.refresh(course)

        # 2. Upload Document & Chunks (Synthetic Syllabus PDF)
        print("[*] Indexing course syllabus document and text chunks...")
        syllabus_doc = Document(
            course_id=course.id,
            filename="CS201_DSA_Syllabus.pdf",
            file_path="uploads/demo/CS201_DSA_Syllabus.pdf",
            file_size=1024 * 350,  # 350 KB
            page_count=18,
            extracted_text_length=12500,
            status=DocumentStatus.COMPLETED.value,
            processed_at=three_days_ago,
            created_at=three_days_ago,
        )
        db.add(syllabus_doc)
        db.commit()
        db.refresh(syllabus_doc)

        syllabus_sections = [
            (1, "Unit 1: Foundations. Arrays and contiguous memory. Strings, immutability, and pattern search. Recursion, base cases, call stacks, and recurrence relations."),
            (2, "Unit 2: Dynamic Programming. Identifying optimal substructure and overlapping subproblems. Defining DP state dp[i][j]. Top-down memoization vs bottom-up tabulation. Grid DP."),
            (3, "Unit 3: Trees. Hierarchical structures, binary trees, tree traversals (preorder, inorder, postorder). Binary Search Trees, BST invariant, insertion, deletion, and searching."),
            (4, "Unit 4: Graph Algorithms. Adjacency list and matrix representations. Breadth-First Search (BFS) for shortest path. Depth-First Search (DFS) for cycle detection. Dijkstra's shortest path algorithm."),
        ]
        for idx, (pg, text_content) in enumerate(syllabus_sections):
            chunk = DocumentChunk(
                document_id=syllabus_doc.id,
                chunk_index=idx,
                content=text_content,
                page_number=pg,
                end_page_number=pg,
                token_count=len(text_content.split()),
                embedding=generate_query_embedding(text_content),
            )
            db.add(chunk)
        db.commit()

        # 3. Create Topics
        print("[*] Creating 14 curriculum topics across 4 Units...")
        topics_spec = [
            # Unit 1
            ("Arrays", "Unit 1: Foundations", "easy", "Contiguous indexed memory structures and amortized resizing."),
            ("Strings", "Unit 1: Foundations", "easy", "Character sequences, ASCII encoding, and substring patterns."),
            ("Recursion", "Unit 1: Foundations", "medium", "Self-referential functions, base cases, and call-stack execution."),
            # Unit 2
            ("Dynamic Programming", "Unit 2: Dynamic Programming", "medium", "Optimization technique breaking problems into overlapping subproblems."),
            ("DP State", "Unit 2: Dynamic Programming", "hard", "Mathematical snapshot representation uniquely identifying subproblems."),
            ("Memoization", "Unit 2: Dynamic Programming", "medium", "Top-down caching of recursive subproblem results."),
            ("Tabulation", "Unit 2: Dynamic Programming", "hard", "Bottom-up iterative population of DP tables."),
            ("Grid DP", "Unit 2: Dynamic Programming", "hard", "2D table transitions for grid pathfinding and matrix costs."),
            # Unit 3
            ("Trees", "Unit 3: Non-Linear Structures", "medium", "Non-linear hierarchical data structures with root and child nodes."),
            ("Binary Trees", "Unit 3: Non-Linear Structures", "medium", "Trees where each node has at most two children."),
            ("Binary Search Trees", "Unit 3: Non-Linear Structures", "hard", "Ordered binary trees enabling O(log N) average lookup."),
            # Unit 4
            ("Graphs", "Unit 4: Advanced Graph Algorithms", "hard", "Vertex and edge networks modeling relational connections."),
            ("BFS", "Unit 4: Advanced Graph Algorithms", "medium", "Breadth-First Search queue traversal for level-order exploration."),
            ("DFS", "Unit 4: Advanced Graph Algorithms", "medium", "Depth-First Search recursive traversal using stack/backtracking."),
            ("Shortest Path", "Unit 4: Advanced Graph Algorithms", "hard", "Finding minimum-cost paths using BFS and Dijkstra's algorithm."),
        ]

        topic_map: dict[str, Topic] = {}
        for name, unit, diff, desc in topics_spec:
            t = Topic(
                course_id=course.id,
                name=name,
                unit_name=unit,
                difficulty=diff,
                description=desc,
                source_type="explicit",
                created_at=three_days_ago,
            )
            db.add(t)
            topic_map[name] = t
        db.commit()

        for t in topic_map.values():
            db.refresh(t)

        # 4. Create Prerequisite Graph (DAG)
        print("[*] Establishing Prerequisite DAG relationships...")
        prereq_edges = [
            ("Recursion", "DP State", 0.95, "DP state transitions directly parameterize recursive subproblem calls."),
            ("DP State", "Memoization", 0.90, "Memoization caches the output of a specific DP state."),
            ("DP State", "Tabulation", 0.90, "Tabulation orders DP state evaluation iteratively."),
            ("Memoization", "Grid DP", 0.85, "Grid DP can be implemented top-down once state is understood."),
            ("Tabulation", "Grid DP", 0.95, "Grid DP typically evaluates cells using 2D bottom-up tabulation."),
            ("Trees", "Binary Trees", 0.95, "Binary trees are specialized trees with branching factor 2."),
            ("Binary Trees", "Binary Search Trees", 0.95, "BSTs add an ordering invariant onto binary trees."),
            ("Graphs", "BFS", 0.90, "BFS is a fundamental traversal algorithm on graphs."),
            ("Graphs", "DFS", 0.90, "DFS is a fundamental traversal algorithm on graphs."),
            ("BFS", "Shortest Path", 0.85, "BFS calculates unweighted shortest paths."),
            ("DFS", "Shortest Path", 0.80, "DFS is used for topological sorting in DAG shortest paths."),
        ]

        for prereq_name, dep_name, conf, reason in prereq_edges:
            prereq_topic = topic_map[prereq_name]
            dep_topic = topic_map[dep_name]
            db.add(
                TopicPrerequisite(
                    topic_id=dep_topic.id,
                    prerequisite_id=prereq_topic.id,
                    confidence=conf,
                    reason=reason,
                )
            )
        db.commit()

        # 5. Diagnostic Assessment Baseline
        print("[*] Generating baseline diagnostic assessment and student attempts...")
        diag_session = DiagnosticSession(
            course_id=course.id,
            user_id=demo_user.id,
            status="completed",
            score=57.1,  # Overall average accuracy across tested topics
            total_questions=35,
            completed_at=three_days_ago,
            created_at=three_days_ago,
        )
        db.add(diag_session)
        db.commit()
        db.refresh(diag_session)

        # Assessment performance profile:
        # Arrays: 5/5 correct (100% -> Strong)
        # Strings: 5/5 correct (100% -> Strong)
        # Recursion: 5/5 correct (100% -> Strong)
        # DP State: 1/5 correct (20% -> Weak)
        # Memoization: 3/5 correct (60% -> Developing)
        # Tabulation: 1/5 correct (20% -> Weak)
        # Grid DP: 0/5 correct (0% -> Weak)
        # Trees: unassessed
        # Graphs: unassessed
        assessed_profile = [
            ("Arrays", 5, 5, 1.00, 0.90, "STRONG"),
            ("Strings", 5, 5, 1.00, 0.90, "STRONG"),
            ("Recursion", 5, 5, 1.00, 0.95, "STRONG"),
            ("DP State", 5, 1, 0.20, 0.85, "WEAK"),
            ("Memoization", 5, 3, 0.60, 0.80, "DEVELOPING"),
            ("Tabulation", 5, 1, 0.20, 0.85, "WEAK"),
            ("Grid DP", 5, 0, 0.00, 0.85, "WEAK"),
        ]

        baseline_question_ids_by_topic: dict[str, list[uuid.UUID]] = {}

        for topic_name, total_q, correct_q, mastery, conf, status_label in assessed_profile:
            t = topic_map[topic_name]
            q_ids = []

            for i in range(total_q):
                is_correct = i < correct_q
                q = Question(
                    topic_id=t.id,
                    question=f"Diagnostic question {i + 1} evaluating {topic_name} fundamentals.",
                    options=["Option A (Incorrect)", "Option B (Correct)", "Option C", "Option D"],
                    correct_answer="Option B (Correct)",
                    explanation=f"Explanation for question {i + 1} in {topic_name}.",
                    difficulty=t.difficulty,
                    source="diagnostic",
                )
                db.add(q)
                db.commit()
                db.refresh(q)
                q_ids.append(q.id)

                # Record attempt linked to diagnostic session
                attempt = Attempt(
                    user_id=demo_user.id,
                    course_id=course.id,
                    topic_id=t.id,
                    question_id=q.id,
                    diagnostic_session_id=diag_session.id,
                    selected_answer="Option B (Correct)" if is_correct else "Option A (Incorrect)",
                    is_correct=is_correct,
                    time_taken=45,
                    created_at=three_days_ago,
                )
                db.add(attempt)

            baseline_question_ids_by_topic[topic_name] = q_ids

            # Baseline TopicMastery
            tm = TopicMastery(
                user_id=demo_user.id,
                topic_id=t.id,
                mastery_score=mastery,
                confidence_score=conf,
                last_assessed_at=three_days_ago,
            )
            db.add(tm)

            # Historical Snapshot 1 (Baseline)
            snap = TopicMasteryHistory(
                user_id=demo_user.id,
                course_id=course.id,
                topic_id=t.id,
                mastery_score=mastery,
                confidence_score=conf,
                evidence_count=total_q,
                assessment_type="DIAGNOSTIC",
                recorded_at=three_days_ago,
            )
            db.add(snap)

        db.commit()

        # 6. Knowledge Gap Analysis
        print("[*] Running Knowledge Gap Analysis identifying root bottlenecks...")
        from app.services.knowledge_gap_service import analyze_knowledge_gaps
        analyze_knowledge_gaps(db, demo_user.id, course.id)

        # 7. Adaptive Study Plan
        print("[*] Generating adaptive study plan prioritizing foundational blockers...")
        from app.services.learning_planner_service import generate_learning_plan
        from app.schemas.study_plan import StudyPlanGeneratePayload

        plan_res = generate_learning_plan(
            db=db,
            user_id=demo_user.id,
            course_id=course.id,
            exam_date=exam_date,
            daily_minutes=45,
            force_regenerate=True,
        )
        plan_id = plan_res.id

        # Mark Recursion as completed (3 days ago)
        recursion_item = db.execute(
            select(PlanItem).where(
                PlanItem.plan_id == plan_id,
                PlanItem.topic_id == topic_map["Recursion"].id,
            )
        ).scalars().first()
        if recursion_item:
            recursion_item.status = "COMPLETED"
            recursion_item.completed_at = three_days_ago

        # Find DP State plan item
        dp_state_item = db.execute(
            select(PlanItem).where(
                PlanItem.plan_id == plan_id,
                PlanItem.topic_id == topic_map["DP State"].id,
            )
        ).scalars().first()
        if dp_state_item:
            dp_state_item.status = "COMPLETED"
            dp_state_item.completed_at = yesterday
            dp_state_item_id = dp_state_item.id
        else:
            dp_state_item_id = None
        db.commit()

        # 8. Completed AI Tutor Session for "DP State"
        print("[*] Recording verified AI Tutor session & dialogue for 'DP State'...")
        dp_topic = topic_map["DP State"]
        tutor_session = TutorSession(
            user_id=demo_user.id,
            course_id=course.id,
            topic_id=dp_topic.id,
            plan_item_id=dp_state_item_id,
            language="hinglish",
            explanation_level="intermediate",
            status=STATUS_COMPLETED,
            current_stage=STAGE_COMPLETED,
            session_metadata={},
            created_at=yesterday,
            updated_at=yesterday,
        )
        db.add(tutor_session)
        db.commit()
        db.refresh(tutor_session)

        # Dialogue Turns
        dialogue = [
            ("USER", "Sir, DP State samajh nahi aa raha. Recursion se kaise relate karein?", "chat"),
            ("ASSISTANT", "DP State basically ek mathematical snapshot hai jo subproblem ko uniquely define karta hai. Agar recursive function me index `i` aur remaining target `W` change ho rahe hain, toh DP state `dp[i][W]` hota hai! [Citation: Unit 2: Dynamic Programming, Page 12]", "explanation"),
            ("USER", "Achha, toh parameters hi state banate hain?", "chat"),
            ("ASSISTANT", "Bilkul sahi! Exactly jo changing parameters hain recursive calls me, wahi aapke DP table ke dimensions bante hain. Chalo ek quick practice question solve karte hain.", "explanation"),
        ]
        for role, content, msg_type in dialogue:
            msg = TutorMessage(
                session_id=tutor_session.id,
                role=role,
                content=content,
                message_type=msg_type,
                related_topic_id=dp_topic.id,
                created_at=yesterday,
            )
            db.add(msg)
        db.commit()

        # 9. Fresh Post-Tutoring Practice Attempts for "DP State" (Verified Learning Improvement!)
        # Crucial: Question IDs must NOT be in the baseline set!
        print("[*] Recording fresh post-tutoring assessment attempts (Verifying observable learning gain)...")
        fresh_correct = 4
        fresh_total = 4
        for i in range(fresh_total):
            fresh_q = Question(
                topic_id=dp_topic.id,
                question=f"Fresh verification problem {i + 1} on DP State parameters.",
                options=["1D State", "2D State dp[i][w]", "No state needed", "Constant time"],
                correct_answer="2D State dp[i][w]",
                explanation="Both index and capacity change, necessitating a 2D state table.",
                difficulty="hard",
                source="tutor_practice",
            )
            db.add(fresh_q)
            db.commit()
            db.refresh(fresh_q)

            fresh_attempt = Attempt(
                user_id=demo_user.id,
                course_id=course.id,
                topic_id=dp_topic.id,
                question_id=fresh_q.id,
                tutor_session_id=tutor_session.id,
                selected_answer="2D State dp[i][w]",
                is_correct=True,
                time_taken=35,
                created_at=yesterday + timedelta(minutes=10 * i),
            )
            db.add(fresh_attempt)

        # Upgrade DP State mastery to 0.85 (Strong!)
        dp_mastery = db.execute(
            select(TopicMastery).where(
                TopicMastery.user_id == demo_user.id,
                TopicMastery.topic_id == dp_topic.id,
            )
        ).scalar_one()
        dp_mastery.mastery_score = 0.85
        dp_mastery.confidence_score = 0.95
        dp_mastery.last_assessed_at = yesterday

        # Historical Snapshot 2 (Post-Tutoring Graduation: Weak -> Strong!)
        snap_post = TopicMasteryHistory(
            user_id=demo_user.id,
            course_id=course.id,
            topic_id=dp_topic.id,
            mastery_score=0.85,
            confidence_score=0.95,
            evidence_count=9,
            assessment_type="TUTOR_PRACTICE",
            recorded_at=yesterday,
        )
        db.add(snap_post)
        db.commit()

        print("\n" + "=" * 70)
        print("  DEMO DATA SUCCESSFULLY SEEDED!")
        print("=" * 70)
        print(f"  Demo Account:  {DEMO_USER_EMAIL}")
        print(f"  Password:      {DEMO_USER_PASSWORD}")
        print(f"  Course:        Data Structures & Algorithms (CS201) [DEMO]")
        print("  Curriculum:    14 Topics across 4 Units")
        print("  Initial Gap:   DP State (20% Baseline) blocking Tabulation & Grid DP")
        print("  Post-Tutoring: DP State fresh assessment (100% Accuracy) -> Mastery upgraded to 85% (+65 pp!)")
        print("=" * 70 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    seed_demo()
