import apiClient from './api';
import {
  ApiResponse,
  PlanItem,
  PlanItemUpdatePayload,
  StudyPlan,
  StudyPlanGeneratePayload,
  StudyPlanHistoryItem,
} from '../types';

/**
 * Generate or regenerate an adaptive learning plan for a course.
 */
export const generateStudyPlan = async (
  courseId: string,
  payload?: StudyPlanGeneratePayload
): Promise<StudyPlan> => {
  const response = await apiClient.post<ApiResponse<StudyPlan>>(
    `/courses/${courseId}/study-plan/generate`,
    payload
  );
  return response.data.data;
};

/**
 * Get the currently active study plan for a course.
 */
export const getActiveStudyPlan = async (courseId: string): Promise<StudyPlan> => {
  const response = await apiClient.get<ApiResponse<StudyPlan>>(
    `/courses/${courseId}/study-plan`
  );
  return response.data.data;
};

/**
 * Get a specific study plan version by plan ID.
 */
export const getStudyPlanById = async (planId: string): Promise<StudyPlan> => {
  const response = await apiClient.get<ApiResponse<StudyPlan>>(
    `/study-plans/${planId}`
  );
  return response.data.data;
};

/**
 * Update the status, duration, or date of a specific study session item.
 */
export const updatePlanItemStatus = async (
  planId: string,
  itemId: string,
  payload: PlanItemUpdatePayload
): Promise<PlanItem> => {
  const response = await apiClient.patch<ApiResponse<PlanItem>>(
    `/study-plans/${planId}/items/${itemId}`,
    payload
  );
  return response.data.data;
};

/**
 * Dynamically rebalance remaining sessions in an active study plan.
 */
export const rebalanceStudyPlan = async (
  planId: string,
  payload?: StudyPlanGeneratePayload
): Promise<StudyPlan> => {
  const response = await apiClient.post<ApiResponse<StudyPlan>>(
    `/study-plans/${planId}/rebalance`,
    payload
  );
  return response.data.data;
};

/**
 * Get the version history of study plans for a course.
 */
export const getStudyPlanHistory = async (
  courseId: string
): Promise<StudyPlanHistoryItem[]> => {
  const response = await apiClient.get<ApiResponse<StudyPlanHistoryItem[]>>(
    `/courses/${courseId}/study-plan/history`
  );
  return response.data.data;
};

