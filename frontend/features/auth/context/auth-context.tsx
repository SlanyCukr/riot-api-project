"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import type { User, LoginCredentials, AuthContextType } from "../types";

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = "auth_token";
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  // Check for token synchronously on initialization to avoid flash
  const [isLoading, setIsLoading] = useState(() => {
    if (typeof window === "undefined") return true;
    return !!localStorage.getItem(TOKEN_KEY);
  });
  const router = useRouter();

  // Check authentication status on mount and after login
  const checkAuth = useCallback(async () => {
    const token = localStorage.getItem(TOKEN_KEY);

    if (!token) {
      setUser(null);
      setIsLoading(false);
      // Ensure cookie is also removed
      document.cookie =
        "auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        // Ensure cookie is in sync with localStorage
        document.cookie = `auth_token=${token}; path=/; max-age=${
          7 * 24 * 60 * 60
        }; SameSite=Lax`;
      } else {
        // Token invalid or expired
        localStorage.removeItem(TOKEN_KEY);
        document.cookie =
          "auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
        setUser(null);
      }
    } catch (error) {
      console.error("Auth check failed:", error);
      localStorage.removeItem(TOKEN_KEY);
      document.cookie =
        "auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initialize auth state on mount
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (credentials: LoginCredentials) => {
    setIsLoading(true);
    try {
      // OAuth2 password flow requires form-data format
      const formData = new URLSearchParams();
      formData.append("username", credentials.email); // OAuth2 uses 'username' field
      formData.append("password", credentials.password);

      const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Login failed");
      }

      const data = await response.json();

      // Store token in localStorage
      localStorage.setItem(TOKEN_KEY, data.access_token);

      // Also store in cookie for middleware access
      document.cookie = `auth_token=${data.access_token}; path=/; max-age=${
        7 * 24 * 60 * 60
      }; SameSite=Lax`;

      // Fetch user data
      await checkAuth();

      // Redirect to home page
      router.push("/");
    } catch (error) {
      setIsLoading(false);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    // Remove cookie
    document.cookie =
      "auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    setUser(null);
    router.push("/sign-in");
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        checkAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
