/**
 * Centralized token management for authentication.
 *
 * This module provides a single source of truth for managing JWT tokens,
 * ensuring localStorage and cookies stay in sync to prevent auth state bugs.
 *
 * Usage:
 *   import { setToken, removeToken, getToken } from '@/features/auth/utils/token-manager'
 *
 *   // On login:
 *   setToken(jwtToken)
 *
 *   // On logout:
 *   removeToken()
 *
 *   // Check for existing token:
 *   const token = getToken()
 */

const TOKEN_KEY = "auth_token";
const TOKEN_MAX_AGE = 7 * 24 * 60 * 60; // 7 days in seconds

/**
 * Set authentication token in both localStorage and cookie.
 *
 * @param token - JWT access token
 */
export function setToken(token: string): void {
  if (typeof window === "undefined") {
    return; // Skip on server-side rendering
  }

  // Store in localStorage for client-side access
  localStorage.setItem(TOKEN_KEY, token);

  // Store in cookie for middleware access
  document.cookie = `${TOKEN_KEY}=${token}; path=/; max-age=${TOKEN_MAX_AGE}; SameSite=Lax`;
}

/**
 * Remove authentication token from both localStorage and cookie.
 */
export function removeToken(): void {
  if (typeof window === "undefined") {
    return; // Skip on server-side rendering
  }

  // Remove from localStorage
  localStorage.removeItem(TOKEN_KEY);

  // Remove cookie by setting expiration to past date
  document.cookie = `${TOKEN_KEY}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
}

/**
 * Get authentication token with priority: localStorage > cookie.
 *
 * @returns JWT token if found, null otherwise
 */
export function getToken(): string | null {
  if (typeof window === "undefined") {
    return null; // Skip on server-side rendering
  }

  // Try localStorage first (primary source)
  const localStorageToken = localStorage.getItem(TOKEN_KEY);
  if (localStorageToken) {
    return localStorageToken;
  }

  // Fallback to cookie if localStorage is empty
  const cookieMatch = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${TOKEN_KEY}=`));

  if (cookieMatch) {
    const token = cookieMatch.split("=")[1];
    // Sync to localStorage if found in cookie but not localStorage
    localStorage.setItem(TOKEN_KEY, token);
    return token;
  }

  return null;
}

/**
 * Check if a valid token exists.
 *
 * @returns true if token exists, false otherwise
 */
export function hasToken(): boolean {
  return getToken() !== null;
}
