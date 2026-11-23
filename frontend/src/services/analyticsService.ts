import apiClient from './api';
import {
  ApiResponse,
  CourseOverviewData,
  TopicMasteryAnalyticsData,
  LearningImprovementData,
  LearningProgressData,
  StudyConsistencyData,
  ExamReadinessData,
  PrerequisiteBlockerItem,
  RecommendationItem,
  FullAnalyticsDashboardData,
} from '../types';

export const getCourseOverview = async (
  courseId: string
): Promise<ApiResponse<CourseOverviewData>> => {
  const response = await apiClient.get<ApiResponse<CourseOverviewData>>(
    `/courses/${encodeURIComponent(courseId)}/analytics/overview`
  );
  return response.data;
};

export const getTopicMasteryAnalytics = async (
  courseId: string
): Promise<ApiResponse<TopicMasteryAnalyticsData>> => {
  const response = await apiClient.get<ApiResponse<TopicMasteryAnalyticsData>>(
    `/courses/${encodeURIComponent(courseId)}/analytics/mastery`
  );
  return response.data;
};

export const getLearningImprovement = async (
  courseId: string
): Promise<ApiResponse<LearningImprovementData>> => {
  const response = await apiClient.get<ApiResponse<LearningImprovementData>>(
    `/courses/${encodeURIComponent(courseId)}/analytics/improvement`
  );
  return response.data;
};

export const getLearningProgress = async (
  courseId: string
): Promise<ApiResponse<LearningProgressData>> => {
  const response = await apiClient.get<ApiResponse<LearningProgressData>>(
    `/courses/${encodeURIComponent(courseId)}/analytics/progress`
  );
  return response.data;
};

export const getStudyConsistency = async (
  courseId: string
): Promise<ApiResponse<StudyConsistencyData>> => {
  const response = await apiClient.get<ApiResponse<StudyConsistencyData>>(
    `/courses/${encodeURIComponent(courseId)}/analytics/consistency`
  );
  return response.data;
};

export const getExamReadiness = async (
  courseId: string
): Promise<ApiResponse<ExamReadinessData>> => {
  const response = await apiClient.get<ApiResponse<ExamReadinessData>>(
    `/courses/${encodeURIComponent(courseId)}/analytics/exam-readiness`
  );
  return response.data;
};

export const getPrerequisiteBottlenecks = async (
  courseId: string
): Promise<ApiResponse<PrerequisiteBlockerItem[]>> => {
  const response = await apiClient.get<ApiResponse<PrerequisiteBlockerItem[]>>(
    `/courses/${encodeURIComponent(courseId)}/analytics/bottlenecks`
  );
  return response.data;
};

export const getRecommendations = async (
  courseId: string
): Promise<ApiResponse<RecommendationItem[]>> => {
  const response = await apiClient.get<ApiResponse<RecommendationItem[]>>(
    `/courses/${encodeURIComponent(courseId)}/analytics/recommendations`
  );
  return response.data;
};

export const getFullAnalyticsDashboard = async (
  courseId: string
): Promise<ApiResponse<FullAnalyticsDashboardData>> => {
  const response = await apiClient.get<ApiResponse<FullAnalyticsDashboardData>>(
    `/courses/${encodeURIComponent(courseId)}/analytics/dashboard`
  );
  return response.data;
};

export const analyticsService = {
  getCourseOverview,
  getTopicMasteryAnalytics,
  getLearningImprovement,
  getLearningProgress,
  getStudyConsistency,
  getExamReadiness,
  getPrerequisiteBottlenecks,
  getRecommendations,
  getFullAnalyticsDashboard,
};

export default analyticsService;

