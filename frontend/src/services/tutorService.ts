import { apiClient } from './api';
import {
  HintData,
  PracticeEvaluationResult,
  PracticeQuestion,
  TeachingStage,
  TutorMessage,
  TutorPreferencesUpdatePayload,
  TutorSessionCreatePayload,
  TutorSessionDetail,
  TutorSourceCitation,
} from '../types';

interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

export interface TutorMessageResponsePayload {
  message: TutorMessage;
  session_id: string;
  current_stage: TeachingStage;
  suggested_next_action: string;
  sources: TutorSourceCitation[];
}

export const startTutorSession = async (
  courseId: string,
  payload: TutorSessionCreatePayload
): Promise<TutorSessionDetail> => {
  const response = await apiClient.post<ApiResponse<TutorSessionDetail>>(
    `/courses/${courseId}/tutor/sessions`,
    payload
  );
  return response.data.data;
};

export const getTutorSession = async (sessionId: string): Promise<TutorSessionDetail> => {
  const response = await apiClient.get<ApiResponse<TutorSessionDetail>>(
    `/tutor/sessions/${sessionId}`
  );
  return response.data.data;
};

export const sendTutorMessage = async (
  sessionId: string,
  message: string
): Promise<TutorMessageResponsePayload> => {
  const response = await apiClient.post<ApiResponse<TutorMessageResponsePayload>>(
    `/tutor/sessions/${sessionId}/messages`,
    { message }
  );
  return response.data.data;
};

export const getSessionMessages = async (sessionId: string): Promise<TutorMessage[]> => {
  const response = await apiClient.get<ApiResponse<TutorMessage[]>>(
    `/tutor/sessions/${sessionId}/messages`
  );
  return response.data.data;
};

export const updateTutorPreferences = async (
  sessionId: string,
  payload: TutorPreferencesUpdatePayload
): Promise<TutorSessionDetail> => {
  const response = await apiClient.patch<ApiResponse<TutorSessionDetail>>(
    `/tutor/sessions/${sessionId}/preferences`,
    payload
  );
  return response.data.data;
};

export const generatePracticeQuestion = async (
  sessionId: string,
  difficulty?: string
): Promise<PracticeQuestion> => {
  const url = difficulty
    ? `/tutor/sessions/${sessionId}/practice?difficulty=${encodeURIComponent(difficulty)}`
    : `/tutor/sessions/${sessionId}/practice`;
  const response = await apiClient.post<ApiResponse<PracticeQuestion>>(url);
  return response.data.data;
};

export const submitPracticeAnswer = async (
  sessionId: string,
  questionId: string,
  answer: string
): Promise<PracticeEvaluationResult & { correct_answer?: string; explanation?: string }> => {
  const response = await apiClient.post<
    ApiResponse<PracticeEvaluationResult & { correct_answer?: string; explanation?: string }>
  >(`/tutor/sessions/${sessionId}/practice/${questionId}/submit`, { answer });
  return response.data.data;
};

export const requestHint = async (
  sessionId: string,
  questionId: string,
  hintLevel: number
): Promise<HintData> => {
  const response = await apiClient.post<ApiResponse<HintData>>(
    `/tutor/sessions/${sessionId}/practice/${questionId}/hint`,
    { hint_level: hintLevel }
  );
  return response.data.data;
};

export const completeTutorSession = async (sessionId: string): Promise<TutorSessionDetail> => {
  const response = await apiClient.post<ApiResponse<TutorSessionDetail>>(
    `/tutor/sessions/${sessionId}/complete`
  );
  return response.data.data;
};

