export interface Course {
  id: string;
  title: string;
  code: string;
  description: string;
  topicCount?: number;
}

export interface Topic {
  id: string;
  name: string;
  category: string;
  difficulty: 'Beginner' | 'Intermediate' | 'Advanced';
  description: string;
  prerequisites: string[];
  order: number;
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

