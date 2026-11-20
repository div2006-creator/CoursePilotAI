import apiClient from './api';
import {
  ApiResponse,
  Course,
  CourseCreatePayload,
  CourseListData,
  CourseUpdatePayload,
} from '../types';

export const createCourse = async (
  payload: CourseCreatePayload
): Promise<ApiResponse<Course>> => {
  const response = await apiClient.post<ApiResponse<Course>>('/courses', payload);
  return response.data;
};

export const getCourses = async (
  search?: string
): Promise<ApiResponse<CourseListData>> => {
  const params = search && search.trim() ? { search: search.trim() } : undefined;
  const response = await apiClient.get<ApiResponse<CourseListData>>('/courses', {
    params,
  });
  return response.data;
};

export const getCourseById = async (
  courseId: string
): Promise<ApiResponse<Course>> => {
  const response = await apiClient.get<ApiResponse<Course>>(
    `/courses/${encodeURIComponent(courseId)}`
  );
  return response.data;
};

export const updateCourse = async (
  courseId: string,
  payload: CourseUpdatePayload
): Promise<ApiResponse<Course>> => {
  const response = await apiClient.patch<ApiResponse<Course>>(
    `/courses/${encodeURIComponent(courseId)}`,
    payload
  );
  return response.data;
};

export const deleteCourse = async (courseId: string): Promise<void> => {
  await apiClient.delete(`/courses/${encodeURIComponent(courseId)}`);
};

export const courseService = {
  createCourse,
  getCourses,
  getCourseById,
  updateCourse,
  deleteCourse,
};

export default courseService;

