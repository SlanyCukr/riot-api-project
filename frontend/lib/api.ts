import axios, { AxiosError } from "axios";
import { z } from "zod";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

export const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000, // 30 second timeout
});

// Enhanced error type
export interface ApiError {
  message: string;
  code?: string;
  status?: number;
  details?: unknown;
}

// Enhanced response type
export type ApiResponse<T> =
  | { success: true; data: T }
  | { success: false; error: ApiError };

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Don't log 404 player-not-found as errors (expected behavior)
    const status = error.response?.status;
    if (status !== 404) {
      console.error("API Error:", error.response?.data || error.message);
    }
    return Promise.reject(error);
  },
);

// Helper to format errors
function formatError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    const detail = error.response?.data?.detail;

    // Handle 404 player not found as expected case
    if (status === 404 && typeof detail === "string") {
      return {
        message: detail,
        code: "PLAYER_NOT_FOUND",
        status: 404,
        details: error.response?.data,
      };
    }

    return {
      message: error.response?.data?.detail || error.message,
      code: error.code,
      status: error.response?.status,
      details: error.response?.data,
    };
  }

  if (error instanceof z.ZodError) {
    return {
      message: "Data validation failed",
      code: "VALIDATION_ERROR",
      details: error.issues,
    };
  }

  if (error instanceof Error) {
    return {
      message: error.message,
      code: "UNKNOWN_ERROR",
    };
  }

  return {
    message: "An unknown error occurred",
    code: "UNKNOWN_ERROR",
  };
}

// Generic validated GET request
export async function validatedGet<T>(
  schema: z.ZodType<T>,
  url: string,
  params?: Record<string, unknown>,
): Promise<ApiResponse<T>> {
  try {
    const response = await api.get(url, { params });
    const parsed = schema.safeParse(response.data);

    if (!parsed.success) {
      return {
        success: false,
        error: formatError(parsed.error),
      };
    }

    return {
      success: true,
      data: parsed.data,
    };
  } catch (error) {
    return {
      success: false,
      error: formatError(error),
    };
  }
}

// Generic validated POST request
export async function validatedPost<T>(
  schema: z.ZodType<T>,
  url: string,
  data?: unknown,
): Promise<ApiResponse<T>> {
  try {
    const response = await api.post(url, data);
    const parsed = schema.safeParse(response.data);

    if (!parsed.success) {
      return {
        success: false,
        error: formatError(parsed.error),
      };
    }

    return {
      success: true,
      data: parsed.data,
    };
  } catch (error) {
    return {
      success: false,
      error: formatError(error),
    };
  }
}

// Generic validated PUT request
export async function validatedPut<T>(
  schema: z.ZodType<T>,
  url: string,
  data?: unknown,
): Promise<ApiResponse<T>> {
  try {
    const response = await api.put(url, data);
    const parsed = schema.safeParse(response.data);

    if (!parsed.success) {
      return {
        success: false,
        error: formatError(parsed.error),
      };
    }

    return {
      success: true,
      data: parsed.data,
    };
  } catch (error) {
    return {
      success: false,
      error: formatError(error),
    };
  }
}

// Generic validated DELETE request
export async function validatedDelete<T>(
  schema: z.ZodType<T>,
  url: string,
): Promise<ApiResponse<T>> {
  try {
    const response = await api.delete(url);
    const parsed = schema.safeParse(response.data);

    if (!parsed.success) {
      return {
        success: false,
        error: formatError(parsed.error),
      };
    }

    return {
      success: true,
      data: parsed.data,
    };
  } catch (error) {
    return {
      success: false,
      error: formatError(error),
    };
  }
}

export default api;
