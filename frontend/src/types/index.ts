export type ExamStatus = 'no_exam_date' | 'passed' | 'today' | 'urgent' | 'upcoming';

export interface Course {
  id: string;
  title: string;
  description: string | null;
  exam_date: string | null;
  daily_minutes: number;
  created_at: string;
  days_remaining: number | null;
  is_exam_passed: boolean;
  exam_status: ExamStatus;
}

export interface CourseCreatePayload {
  title: string;
  description?: string | null;
  exam_date?: string | null;
  daily_minutes: number;
}

export interface CourseUpdatePayload {
  title?: string;
  description?: string | null;
  exam_date?: string | null;
  daily_minutes?: number;
}

export interface CourseListData {
  courses: Course[];
  total: number;
}

export interface Subtopic {
  id: string;
  name: string;
  description: string | null;
  difficulty: string;
  parent_id: string | null;
}

export interface PrerequisiteLink {
  id: string;
  name: string;
  confidence: number;
  reason: string | null;
}

export interface Topic {
  id: string;
  course_id: string;
  name: string;
  description: string | null;
  difficulty: 'easy' | 'medium' | 'hard' | string;
  parent_id: string | null;
  unit_name: string | null;
  source_type: 'explicit' | 'inferred' | string;
  source_pages: number[] | null;
  created_at: string;
  subtopics: Subtopic[];
}

export interface TopicDetail extends Topic {
  prerequisites: PrerequisiteLink[];
  dependents: PrerequisiteLink[];
}

export interface UnitGroup {
  unit_name: string;
  topics: Topic[];
}

export interface CourseTopicsData {
  units: UnitGroup[];
  total_units: number;
  total_topics: number;
  total_subtopics: number;
}

export interface TopicUpdatePayload {
  name?: string;
  description?: string | null;
  difficulty?: string;
  unit_name?: string | null;
}

export interface TopicGraphNode {
  id: string;
  label: string;
  unit: string | null;
  difficulty: string;
  source_type: string;
  description: string | null;
  parent_id: string | null;
  subtopic_count: number;
}

export interface TopicGraphEdge {
  source: string; // Prerequisite topic id
  target: string; // Dependent topic id
  relationship: string;
  confidence: number;
  reason: string | null;
}

export interface TopicGraphData {
  nodes: TopicGraphNode[];
  edges: TopicGraphEdge[];
  total_nodes: number;
  total_edges: number;
  is_dag: boolean;
}

export interface TopicExtractionData {
  course_id: string;
  units_extracted: number;
  topics_created: number;
  subtopics_created: number;
  prerequisites_created: number;
  sample_topics: string[];
}

export interface MasteryScore {
  topicId: string;
  topicName: string;
  score: number; // 0.0 to 1.0
  status: 'weak' | 'moderate' | 'mastered';
}

export interface StudyPlanItem {
  id: string;
  day: number;
  topicId: string;
  topicName: string;
  activity: string;
  estimatedHours: number;
  completed: boolean;
}

export interface HealthStatus {
  status: string;
  app_name: string;
  version: string;
  timestamp: string;
  environment: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message: string;
}

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  created_at: string;
}

export interface RegisterPayload {
  name: string;
  email: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TokenData {
  access_token: string;
  token_type: string;
}

export interface DiagnosticStartPayload {
  mode: 'full' | 'selected';
  topic_ids?: string[];
  difficulty?: 'easy' | 'medium' | 'hard' | 'mixed';
  questions_per_topic?: number;
}

export interface QuestionPublic {
  id: string;
  topic_id: string;
  topic_name: string;
  question: string;
  options: string[];
  difficulty: string;
}

export interface DiagnosticQuestionsData {
  session_id: string;
  course_id: string;
  mode: string;
  status: string;
  total_questions: number;
  questions: QuestionPublic[];
}

export interface AnswerSubmission {
  question_id: string;
  selected_answer: string;
  time_taken: number;
}

export interface TopicAccuracy {
  topic_id: string;
  topic_name: string;
  total_questions: number;
  correct_answers: number;
  accuracy_percentage: number;
  status: 'strong' | 'moderate' | 'weak' | 'not_assessed';
}

export interface DifficultyBreakdown {
  difficulty: string;
  total: number;
  correct: number;
  accuracy_percentage: number;
}

export interface QuestionReview {
  question_id: string;
  topic_id: string;
  topic_name: string;
  question: string;
  options: string[];
  selected_answer: string;
  correct_answer: string;
  is_correct: boolean;
  explanation: string | null;
  time_taken: number;
}

export interface DiagnosticResultData {
  session_id: string;
  course_id: string;
  mode: string;
  status: string;
  score: number;
  total_questions: number;
  correct_answers: number;
  incorrect_answers: number;
  duration_seconds: number;
  topic_accuracies: TopicAccuracy[];
  difficulty_breakdown: DifficultyBreakdown[];
  strongest_topics: string[];
  weak_topics: string[];
  questions_review: QuestionReview[];
}

export interface DiagnosticHistoryItem {
  session_id: string;
  course_id: string;
  mode: string;
  status: string;
  score: number;
  total_questions: number;
  correct_answers: number;
  started_at: string;
  completed_at: string | null;
}

export interface TopicPerformanceMetric {
  topic_id: string;
  topic_name: string;
  total_attempts: number;
  correct_attempts: number;
  accuracy_percentage: number;
  knowledge_status: 'strong' | 'developing' | 'weak' | 'not_assessed';
  confidence_score: number;
  last_attempted_at: string | null;
  unit_name?: string | null;
}

export interface PrerequisiteNode {
  topic_id: string;
  topic_name: string;
  knowledge_status: string;
  accuracy_percentage: number;
  depth: number;
  is_direct: boolean;
}

export type KnowledgeGapType =
  | 'direct_weakness'
  | 'foundational_weakness'
  | 'potential_knowledge_gap'
  | 'isolated_difficulty';

export interface KnowledgeGapDetail {
  id?: string | null;
  topic_id: string;
  topic_name: string;
  gap_type: KnowledgeGapType;
  severity: number;
  confidence: number;
  accuracy_percentage: number;
  attempt_count: number;
  evidence: Record<string, any>;
  recommendation?: string | null;
  prerequisite_chain: PrerequisiteNode[];
}

export interface GapRecommendationItem {
  priority: number;
  topic_id: string;
  topic_name: string;
  action_type: 'revise_prerequisite' | 'practice_topic' | 'take_diagnostic';
  reason: string;
  severity: number;
}

export interface KnowledgeGapAnalysisData {
  analysis_id: string;
  course_id: string;
  diagnostic_session_id?: string | null;
  status: string;
  overall_gap_score: number;
  created_at: string;
  summary: string;
  total_topics: number;
  assessed_topics: number;
  strong_topics_count: number;
  developing_topics_count: number;
  weak_topics_count: number;
  unassessed_topics_count: number;
  topic_performances: TopicPerformanceMetric[];
  gaps: KnowledgeGapDetail[];
  recommendations: GapRecommendationItem[];
}

export interface KnowledgeGapHistoryItem {
  analysis_id: string;
  course_id: string;
  overall_gap_score: number;
  weak_topics_count: number;
  created_at: string;
}

export interface ReassessPayload {
  difficulty?: 'easy' | 'medium' | 'hard' | 'mixed';
  questions_per_topic?: number;
}

// ---------------------------------------------------------------------------
// Part 9: Adaptive Learning Planner Types
// ---------------------------------------------------------------------------

export type SessionType = 'LEARN' | 'PRACTICE' | 'REVISION' | 'ASSESSMENT' | string;
export type PlanItemStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'SKIPPED' | string;

export interface PlanItem {
  id: string;
  plan_id: string;
  topic_id: string;
  topic_name: string;
  unit_name: string | null;
  difficulty: string;
  scheduled_date: string;
  duration_minutes: number;
  priority_score: number;
  session_type: SessionType;
  status: PlanItemStatus;
  sequence_number: number;
  created_at: string;
  completed_at: string | null;
  is_prerequisite_satisfied: boolean;
  unmet_prerequisites: string[];
}

export interface DayScheduleGroup {
  date: string;
  day_number: number;
  total_minutes: number;
  is_exam_day: boolean;
  is_final_revision_day: boolean;
  sessions: PlanItem[];
}

export interface StudyPlanProgress {
  total_items: number;
  completed_items: number;
  in_progress_items: number;
  pending_items: number;
  skipped_items: number;
  completion_percentage: number;
  total_minutes_scheduled: number;
  completed_minutes: number;
  days_remaining: number | null;
  target_exam_date: string | null;
  daily_minutes_target: number;
  unslotted_topics_count: number;
  unslotted_topic_names: string[];
  is_on_track: boolean;
}

export interface StudyPlan {
  id: string;
  course_id: string;
  course_title: string;
  version: number;
  status: string;
  created_at: string;
  exam_date: string | null;
  daily_minutes: number;
  summary: string | null;
  progress: StudyPlanProgress;
  days: DayScheduleGroup[];
}

export interface StudyPlanHistoryItem {
  id: string;
  course_id: string;
  version: number;
  status: string;
  created_at: string;
  exam_date: string | null;
  daily_minutes: number;
  total_items: number;
  completed_items: number;
  completion_percentage: number;
}

export interface StudyPlanGeneratePayload {
  exam_date?: string | null;
  daily_minutes?: number | null;
  force_regenerate?: boolean;
}

export interface PlanItemUpdatePayload {
  status?: PlanItemStatus;
  duration_minutes?: number;
  scheduled_date?: string;
}

// ---------------------------------------------------------------------------
// Part 10: Personalized AI Tutor Types
// ---------------------------------------------------------------------------

export type TeachingStage =
  | 'DIAGNOSIS'
  | 'EXPLANATION'
  | 'EXAMPLE'
  | 'PRACTICE'
  | 'VERIFICATION'
  | 'COMPLETED';

export type ExplanationLevel = 'beginner' | 'intermediate' | 'advanced';

export type TutorLanguage = 'english' | 'hindi' | 'hinglish';

export type TutorSessionStatus = 'active' | 'completed' | 'abandoned';

export type TutorRole = 'user' | 'assistant' | 'system';

export type TutorMessageType =
  | 'text'
  | 'explanation'
  | 'example'
  | 'practice_question'
  | 'hint'
  | 'evaluation'
  | 'system';

export interface TutorSourceCitation {
  document_id?: string;
  unit_name?: string;
  page_number?: number;
  section_title?: string;
  snippet?: string;
}

export interface TutorMessage {
  id: string;
  session_id: string;
  role: TutorRole;
  content: string;
  message_type: TutorMessageType;
  related_topic_id: string | null;
  sources: TutorSourceCitation[];
  created_at: string;
}

export interface TutorSessionMetadata {
  teaching_step?: number;
  hints_used?: number;
  practice_questions_solved?: number;
  consecutive_correct?: number;
  consecutive_incorrect?: number;
  suggested_next_action?: string;
  current_question_id?: string;
  [key: string]: unknown;
}

export interface TutorSession {
  id: string;
  user_id: string;
  course_id: string;
  topic_id: string;
  plan_item_id: string | null;
  language: TutorLanguage;
  explanation_level: ExplanationLevel;
  status: TutorSessionStatus;
  current_stage: TeachingStage;
  session_metadata: TutorSessionMetadata;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface TutorSessionDetail extends TutorSession {
  topic_name: string;
  course_title: string;
  recent_messages: TutorMessage[];
}

export interface TutorSessionCreatePayload {
  topic_id: string;
  plan_item_id?: string | null;
  language?: TutorLanguage;
  explanation_level?: ExplanationLevel;
}

export interface TutorMessageCreatePayload {
  message: string;
  context_override?: Record<string, unknown>;
}

export interface TutorPreferencesUpdatePayload {
  language?: TutorLanguage;
  explanation_level?: ExplanationLevel;
  current_stage?: TeachingStage;
}

export interface PracticeQuestion {
  id: string;
  topic_id: string;
  topic_name: string;
  question: string;
  question_type: string;
  options: string[];
  difficulty: string;
}

export interface PracticeEvaluationResult {
  is_correct: boolean;
  score: number;
  feedback: string;
  strengths: string[];
  errors_identified: string[];
  misconceptions: string[];
  next_step_advice: string;
  updated_mastery_score: number;
  updated_confidence_score: number;
}

export interface HintData {
  question_id: string;
  hint_level: number;
  hint: string;
  is_final_hint: boolean;
  instruction: string;
}




// ============================================================================
// PART 11: Learning Analytics & Adaptive Progress Intelligence Types
// ============================================================================

export interface CourseOverviewData {
  total_topics: number;
  assessed_topics: number;
  strong_topics: number;
  developing_topics: number;
  weak_topics: number;
  unassessed_topics: number;
  completed_study_sessions: number;
  pending_study_sessions: number;
  total_practice_attempts: number;
  average_mastery_percentage: number | null;
  active_plan_id: string | null;
  active_plan_version: number | null;
  exam_date: string | null;
  days_remaining: number | null;
}

export interface TopicMasteryItem {
  topic_id: string;
  topic_name: string;
  unit_name: string | null;
  difficulty: string;
  mastery_score: number | null;
  mastery_percentage: number | null;
  previous_mastery_score: number | null;
  mastery_change: number | null;
  diagnostic_accuracy: number | null;
  latest_practice_accuracy: number | null;
  evidence_count: number;
  last_assessed_at: string | null;
  learning_status: 'STRONG' | 'DEVELOPING' | 'WEAK' | 'NOT_ASSESSED' | string;
  is_prerequisite_satisfied: boolean;
  unmet_prerequisites: string[];
  recommended_action: string;
}

export interface TopicMasteryAnalyticsData {
  topics: TopicMasteryItem[];
  total_count: number;
  strong_count: number;
  developing_count: number;
  weak_count: number;
  unassessed_count: number;
}

export interface DiagnosticComparisonItem {
  topic_id: string;
  topic_name: string;
  unit_name: string | null;
  baseline_score: number;
  latest_score: number | null;
  percentage_point_improvement: number | null;
  baseline_questions_count: number;
  latest_questions_count: number;
  baseline_date: string;
  latest_date: string | null;
  evidence_quality: 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT' | string;
  is_fresh: boolean;
  status_label: string;
}

export interface LearningImprovementData {
  has_sufficient_data: boolean;
  total_comparisons: number;
  improved_topics_count: number;
  stagnant_topics_count: number;
  regressed_topics_count: number;
  average_percentage_point_change: number | null;
  comparisons: DiagnosticComparisonItem[];
  explanation: string;
}

export interface LearningVelocityData {
  topics_improved_7d: number;
  topics_improved_30d: number;
  average_mastery_change: number | null;
  transitions_weak_to_developing: number;
  transitions_developing_to_strong: number;
  velocity_status: 'ACCELERATING' | 'STEADY' | 'EARLY_STAGE' | 'NEEDS_PRACTICE' | string;
  velocity_description: string;
}

export interface LearningProgressPoint {
  date: string;
  average_mastery: number;
  assessed_topics_count: number;
}

export interface LearningProgressData {
  history_points: LearningProgressPoint[];
  velocity: LearningVelocityData;
}

export interface DailyActivityPoint {
  date: string;
  completed_sessions: number;
  practice_attempts: number;
  minutes_spent: number;
}

export interface StudyConsistencyData {
  completed_sessions: number;
  skipped_sessions: number;
  pending_sessions: number;
  total_scheduled: number;
  completion_rate: number;
  active_study_days: number;
  current_streak_days: number;
  daily_activity: DailyActivityPoint[];
  streak_description: string;
}

export interface PrerequisiteBlockerItem {
  topic_id: string;
  topic_name: string;
  unit_name: string | null;
  mastery_score: number | null;
  mastery_percentage: number | null;
  dependent_topics_count: number;
  blocked_topics_names: string[];
  bottleneck_impact_score: number;
  explanation: string;
  action_url: string;
}

export interface ExamReadinessData {
  readiness_score: number;
  category: 'Exam Ready' | 'Almost Ready' | 'Needs More Practice' | 'At Risk' | string;
  is_reliable: boolean;
  assessment_coverage_percentage: number;
  coverage_warning: string | null;
  mastery_component: number;
  importance_component: number;
  prerequisite_component: number;
  recent_performance_component: number;
  coverage_component: number;
  exam_date: string | null;
  days_remaining: number | null;
  strong_topics_count: number;
  weak_topics_count: number;
  unassessed_topics_count: number;
  blocking_prerequisites_count: number;
  recommended_actions: string[];
}

export interface RecommendationItem {
  id: string;
  title: string;
  description: string;
  reason: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW' | string;
  action_type: 'TUTOR' | 'PRACTICE' | 'DIAGNOSTIC' | 'STUDY_PLAN' | string;
  action_url: string;
  related_topic_id: string | null;
  supporting_evidence: string;
}

export interface FullAnalyticsDashboardData {
  overview: CourseOverviewData;
  mastery_analytics: TopicMasteryAnalyticsData;
  improvement: LearningImprovementData;
  progress: LearningProgressData;
  consistency: StudyConsistencyData;
  exam_readiness: ExamReadinessData;
  bottlenecks: PrerequisiteBlockerItem[];
  recommendations: RecommendationItem[];
}

// ============================================================================
// PART 5: Document Upload & PDF Processing Types
// ============================================================================

export interface CourseDocument {
  id: string;
  course_id: string;
  filename: string;
  file_size: number | null;
  page_count: number | null;
  extracted_text_length: number | null;
  chunk_count: number;
  status: 'uploaded' | 'processing' | 'completed' | 'failed' | 'ocr_required' | string;
  error_message: string | null;
  processed_at: string | null;
  created_at: string;
}

export interface CourseDocumentChunk {
  id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  page_number: number | null;
  end_page_number: number | null;
  token_count: number | null;
}

export interface CourseDocumentListData {
  documents: CourseDocument[];
  total: number;
}
