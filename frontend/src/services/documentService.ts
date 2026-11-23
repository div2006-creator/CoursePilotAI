import apiClient from './api';
import {
  ApiResponse,
  CourseDocument,
  CourseDocumentListData,
} from '../types';

export const getCourseDocuments = async (
  courseId: string
): Promise<ApiResponse<CourseDocumentListData>> => {
  const response = await apiClient.get<ApiResponse<CourseDocumentListData>>(
    `/courses/${encodeURIComponent(courseId)}/documents`
  );
  return response.data;
};

export const uploadCourseDocument = async (
  courseId: string,
  file: File
): Promise<ApiResponse<CourseDocument>> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<ApiResponse<CourseDocument>>(
    `/courses/${encodeURIComponent(courseId)}/documents/upload`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
  return response.data;
};

export const deleteCourseDocument = async (
  courseId: string,
  documentId: string
): Promise<void> => {
  await apiClient.delete(
    `/courses/${encodeURIComponent(courseId)}/documents/${encodeURIComponent(documentId)}`
  );
};

export const retryCourseDocument = async (
  courseId: string,
  documentId: string
): Promise<ApiResponse<CourseDocument>> => {
  const response = await apiClient.post<ApiResponse<CourseDocument>>(
    `/courses/${encodeURIComponent(courseId)}/documents/${encodeURIComponent(documentId)}/retry`
  );
  return response.data;
};

export const documentService = {
  getCourseDocuments,
  uploadCourseDocument,
  deleteCourseDocument,
  retryCourseDocument,
};

export default documentService;

