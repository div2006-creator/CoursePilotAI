import apiClient from './api';
import {
  ApiResponse,
  AuthUser,
  LoginPayload,
  RegisterPayload,
  TokenData,
} from '../types';
import { clearAccessToken, setAccessToken } from '../utils/tokenStorage';

export const register = async (
  payload: RegisterPayload
): Promise<ApiResponse<AuthUser>> => {
  const response = await apiClient.post<ApiResponse<AuthUser>>(
    '/auth/register',
    payload
  );
  return response.data;
};

export const login = async (
  payload: LoginPayload
): Promise<ApiResponse<TokenData>> => {
  const response = await apiClient.post<ApiResponse<TokenData>>(
    '/auth/login',
    payload
  );
  const accessToken = response.data?.data?.access_token;
  if (accessToken) {
    setAccessToken(accessToken);
  }
  return response.data;
};

export const getCurrentUser = async (): Promise<ApiResponse<AuthUser>> => {
  const response = await apiClient.get<ApiResponse<AuthUser>>('/auth/me');
  return response.data;
};

export const logout = (): void => {
  clearAccessToken();
};

export const authService = {
  register,
  login,
  getCurrentUser,
  logout,
};

export default authService;

