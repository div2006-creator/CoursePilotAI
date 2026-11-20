import apiClient from './api';
import {
  ApiResponse,
  CourseTopicsData,
  TopicDetail,
  TopicExtractionData,
  TopicGraphData,
  TopicUpdatePayload,
} from '../types';

export const extractTopics = async (
  courseId: string
): Promise<ApiResponse<TopicExtractionData>> => {
  const response = await apiClient.post<ApiResponse<TopicExtractionData>>(
    `/courses/${encodeURIComponent(courseId)}/extract-topics`
  );
  return response.data;
};

export const getCourseTopics = async (
  courseId: string
): Promise<ApiResponse<CourseTopicsData>> => {
  const response = await apiClient.get<ApiResponse<CourseTopicsData>>(
    `/courses/${encodeURIComponent(courseId)}/topics`
  );
  return response.data;
};

export const getTopicGraph = async (
  courseId: string
): Promise<ApiResponse<TopicGraphData>> => {
  const response = await apiClient.get<ApiResponse<TopicGraphData>>(
    `/courses/${encodeURIComponent(courseId)}/topic-graph`
  );
  return response.data;
};

export const getTopicById = async (
  topicId: string
): Promise<ApiResponse<TopicDetail>> => {
  const response = await apiClient.get<ApiResponse<TopicDetail>>(
    `/topics/${encodeURIComponent(topicId)}`
  );
  return response.data;
};

export const updateTopic = async (
  topicId: string,
  payload: TopicUpdatePayload
): Promise<ApiResponse<TopicDetail>> => {
  const response = await apiClient.patch<ApiResponse<TopicDetail>>(
    `/topics/${encodeURIComponent(topicId)}`,
    payload
  );
  return response.data;
};

export const deleteTopic = async (topicId: string): Promise<void> => {
  await apiClient.delete(`/topics/${encodeURIComponent(topicId)}`);
};

export const topicService = {
  extractTopics,
  getCourseTopics,
  getTopicGraph,
  getTopicById,
  updateTopic,
  deleteTopic,
};

export default topicService;

