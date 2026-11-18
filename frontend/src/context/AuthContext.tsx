import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { registerUnauthorizedHandler } from '../services/api';
import authService from '../services/authService';
import { AuthUser, LoginPayload, RegisterPayload } from '../types';
import { clearAccessToken, getAccessToken } from '../utils/tokenStorage';

export interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
  }, []);

  // Sync context state if Axios interceptor receives HTTP 401
  useEffect(() => {
    registerUnauthorizedHandler(() => {
      setUser(null);
    });
    return () => {
      registerUnauthorizedHandler(null);
    };
  }, []);

  // Rehydrate current user session on app startup if a token is stored
  useEffect(() => {
    let isMounted = true;

    const initializeAuth = async () => {
      const token = getAccessToken();
      if (!token) {
        if (isMounted) {
          setIsLoading(false);
        }
        return;
      }

      try {
        const res = await authService.getCurrentUser();
        if (isMounted && res.success && res.data) {
          setUser(res.data);
        } else if (isMounted) {
          clearAccessToken();
          setUser(null);
        }
      } catch {
        clearAccessToken();
        if (isMounted) {
          setUser(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void initializeAuth();

    return () => {
      isMounted = false;
    };
  }, []);

  const login = useCallback(async (payload: LoginPayload) => {
    await authService.login(payload);
    const meResponse = await authService.getCurrentUser();
    setUser(meResponse.data);
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    await authService.register(payload);
    await authService.login({
      email: payload.email,
      password: payload.password,
    });
    const meResponse = await authService.getCurrentUser();
    setUser(meResponse.data);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      login,
      register,
      logout,
    }),
    [user, isLoading, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextValue => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

