import { useState, useCallback } from "react";
import api from "../utils/api";

interface UseApiOptions {
  onSuccess?: (data: any) => void;
  onError?: (error: any) => void;
}

export function useApi<T = any>() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const get = useCallback(
    async (
      endpoint: string,
      params?: Record<string, any>,
      options: UseApiOptions = {},
    ): Promise<T | null> => {
      setLoading(true);
      setError(null);

      try {
        const response = await api.get(endpoint, { params });
        const data = response.data;

        if (options.onSuccess) {
          options.onSuccess(data);
        }

        return data;
      } catch (err: any) {
        const errorMessage = err.response?.data?.detail || err.message;
        setError(errorMessage);

        if (options.onError) {
          options.onError(err);
        }

        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const post = useCallback(
    async (
      endpoint: string,
      data: any,
      options: UseApiOptions = {},
    ): Promise<T | null> => {
      setLoading(true);
      setError(null);

      try {
        const response = await api.post(endpoint, data);
        const result = response.data;

        if (options.onSuccess) {
          options.onSuccess(result);
        }

        return result;
      } catch (err: any) {
        const errorMessage = err.response?.data?.detail || err.message;
        setError(errorMessage);

        if (options.onError) {
          options.onError(err);
        }

        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  return { loading, error, get, post, setError };
}
