-- =============================================================================
-- CoursePilot AI - Initial Database Initialization Schema
-- Database: PostgreSQL 16+ with pgvector extension
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- PLACEHOLDER FOR FUTURE TABLES
-- Full domain tables to be implemented in subsequent phases:
--
-- 1. users & auth
--    - id (UUID), email, hashed_password, full_name, role, created_at, updated_at
--
-- 2. courses & syllabi
--    - id (UUID), title, code, description, raw_text, parsed_metadata
--
-- 3. topics & prerequisite_graph
--    - id (UUID), course_id, title, slug, description, difficulty, order_index
--    - prerequisite_edges: (source_topic_id, target_topic_id, relationship_type)
--
-- 4. diagnostic_assessments & question_bank
--    - id (UUID), topic_id, question_text, question_type, options, correct_answer, explanation
--    - assessment_submissions: (user_id, assessment_id, score, answers, completed_at)
--
-- 5. student_mastery & learning_profiles
--    - user_id, topic_id, mastery_score (0.0 - 1.0), confidence_level, last_evaluated_at
--
-- 6. study_plans & milestones
--    - id (UUID), user_id, course_id, target_date, status, plan_json, generated_at
--
-- 7. rag_documents & vector_embeddings
--    - id (UUID), document_name, chunk_index, content, embedding vector(384/768/1536), metadata
--
-- 8. tutor_chat_sessions & messages
--    - session_id (UUID), user_id, role (user/assistant/system), content, sources, created_at
-- =============================================================================

