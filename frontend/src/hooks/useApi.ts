import { useState, useCallback } from 'react';
import api from '../utils/api';

interface UseApiOptions {
  onSuccess?: (data: any) => void;
  onError?: (error: any) => void;
}

export function useApi<T = any>() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const request = useCallback(async (
    endpoint: string,
    options: UseApiOptions = {}
  ): Promise<T | null> => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.get(endpoint);
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
  }, []);

  const post = useCallback(async (
    endpoint: string,
    data: any,
    options: UseApiOptions = {}
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
  }, []);

  return { loading, error, request, post, setError };
}