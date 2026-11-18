/**
 * Isolated JWT bearer token storage module for CoursePilot AI.
 *
 * Security Note (Hackathon Demo Trade-Off):
 * -----------------------------------------
 * This module persists the JWT access token in `window.localStorage` so the
 * Vite SPA and FastAPI backend work seamlessly across reloads without requiring
 * HTTPS/SameSite cookie configuration during local development.
 *
 * Trade-off: Tokens in `localStorage` are accessible to JavaScript running in
 * the origin, which increases exposure if an XSS vulnerability is introduced.
 * Passwords are NEVER stored here or anywhere in browser storage.
 *
 * Production Migration Path: Replace these three functions with backend-issued
 * `HttpOnly`, `Secure`, `SameSite=Lax` cookies (and CSRF protection) without
 * changing call sites in `AuthContext` or `authService`.
 */

const ACCESS_TOKEN_STORAGE_KEY = 'coursepilot_access_token';

export const getAccessToken = (): string | null => {
  try {
    return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
};

export const setAccessToken = (token: string): void => {
  try {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
  } catch {
    // Ignore storage quota or privacy-mode errors gracefully
  }
};

export const clearAccessToken = (): void => {
  try {
    window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
  } catch {
    // Ignore storage errors gracefully
  }
};

