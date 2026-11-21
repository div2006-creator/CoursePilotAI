import apiClient from './api';
import {
  ApiResponse,
  DiagnosticQuestionsData,
  GapRecommendationItem,
  KnowledgeGapAnalysisData,
  KnowledgeGapDetail,
  KnowledgeGapHistoryItem,
  ReassessPayload,
} from '../types';

export const analyzeKnowledgeGaps = async (
  courseId: string
): Promise<KnowledgeGapAnalysisData> => {
  const response = await apiClient.post<ApiResponse<KnowledgeGapAnalysisData>>(
    `/courses/${courseId}/knowledge-gaps/analyze`
  );
  return response.data.data;
};

export const getKnowledgeGaps = async (
  courseId: string
): Promise<KnowledgeGapAnalysisData> => {
  const response = await apiClient.get<ApiResponse<KnowledgeGapAnalysisData>>(
    `/courses/${courseId}/knowledge-gaps`
  );
  return response.data.data;
};

export const getKnowledgeGapHistory = async (
  courseId: string
): Promise<KnowledgeGapHistoryItem[]> => {
  const response = await apiClient.get<ApiResponse<KnowledgeGapHistoryItem[]>>(
    `/courses/${courseId}/knowledge-gaps/history`
  );
  return response.data.data;
};

export const getTopicKnowledgeGap = async (
  topicId: string
): Promise<KnowledgeGapDetail | null> => {
  const response = await apiClient.get<ApiResponse<KnowledgeGapDetail | null>>(
    `/topics/${topicId}/knowledge-gaps`
  );
  return response.data.data;
};

export const getGapRecommendations = async (
  courseId: string
): Promise<GapRecommendationItem[]> => {
  const response = await apiClient.get<ApiResponse<GapRecommendationItem[]>>(
    `/courses/${courseId}/knowledge-gaps/recommendations`
  );
  return response.data.data;
};

export const reassessPrerequisites = async (
  courseId: string,
  payload?: ReassessPayload
): Promise<DiagnosticQuestionsData> => {
  const response = await apiClient.post<DiagnosticQuestionsData>(
    `/courses/${courseId}/knowledge-gaps/reassess`,
    payload || {}
  );
  return response.data;
};

