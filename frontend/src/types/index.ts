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

export interface TutorMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  citations?: Array<{
    document: string;
    page: number;
    snippet: string;
  }>;
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


