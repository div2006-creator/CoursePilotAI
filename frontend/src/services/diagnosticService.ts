import apiClient from './api';
import {
  AnswerSubmission,
  ApiResponse,
  DiagnosticHistoryItem,
  DiagnosticQuestionsData,
  DiagnosticResultData,
  DiagnosticStartPayload,
} from '../types';

export const startDiagnostic = async (
  courseId: string,
  payload: DiagnosticStartPayload
): Promise<DiagnosticQuestionsData> => {
  const response = await apiClient.post<DiagnosticQuestionsData>(
    `/courses/${courseId}/diagnostic/start`,
    payload
  );
  return response.data;
};

export const getDiagnosticQuestions = async (
  diagnosticId: string
): Promise<DiagnosticQuestionsData> => {
  const response = await apiClient.get<DiagnosticQuestionsData>(
    `/diagnostic/${diagnosticId}/questions`
  );
  return response.data;
};

export const submitDiagnostic = async (
  diagnosticId: string,
  answers: AnswerSubmission[]
): Promise<DiagnosticResultData> => {
  const response = await apiClient.post<ApiResponse<DiagnosticResultData>>(
    `/diagnostic/${diagnosticId}/submit`,
    { answers }
  );
  return response.data.data;
};

export const getDiagnosticResult = async (
  diagnosticId: string
): Promise<DiagnosticResultData> => {
  const response = await apiClient.get<ApiResponse<DiagnosticResultData>>(
    `/diagnostic/${diagnosticId}/result`
  );
  return response.data.data;
};

export const getDiagnosticHistory = async (
  courseId: string
): Promise<DiagnosticHistoryItem[]> => {
  const response = await apiClient.get<ApiResponse<DiagnosticHistoryItem[]>>(
    `/courses/${courseId}/diagnostic/history`
  );
  return response.data.data;
};

