import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { HealthStatus } from '../types';
import { clearAccessToken, getAccessToken } from '../utils/tokenStorage';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

type UnauthorizedCallback = () => void;
let unauthorizedHandler: UnauthorizedCallback | null = null;

export const registerUnauthorizedHandler = (
  handler: UnauthorizedCallback | null
): void => {
  unauthorizedHandler = handler;
};

// Attach JWT bearer token to outgoing API requests when available
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Clear invalid auth state when an authenticated request fails with HTTP 401
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const statusCode = error.response?.status;
    const requestUrl = error.config?.url || '';
    const isAuthAttempt =
      requestUrl.includes('/auth/login') || requestUrl.includes('/auth/register');

    if (statusCode === 401 && !isAuthAttempt) {
      clearAccessToken();
      if (unauthorizedHandler) {
        unauthorizedHandler();
      }
    }

    return Promise.reject(error);
  }
);

export const extractApiErrorMessage = (
  error: unknown,
  fallbackMessage = 'An unexpected error occurred. Please try again.'
): string => {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as
      | { message?: string; detail?: string | Array<{ msg?: string }> }
      | undefined;

    if (data?.message && typeof data.message === 'string') {
      return data.message;
    }
    if (typeof data?.detail === 'string') {
      return data.detail;
    }
    if (Array.isArray(data?.detail) && data.detail.length > 0 && data.detail[0]?.msg) {
      return data.detail[0].msg;
    }
    if (!error.response) {
      return 'Unable to reach the server. Please check that the backend API is running.';
    }
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallbackMessage;
};

export const checkHealth = async (): Promise<HealthStatus> => {
  const response = await apiClient.get<HealthStatus>('/health');
  return response.data;
};

export default apiClient;
