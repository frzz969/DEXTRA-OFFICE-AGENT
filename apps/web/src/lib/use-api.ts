'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError } from './api';

export interface ApiQueryState<T> {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
  refresh: () => void;
}

/**
 * Ambil satu endpoint dengan status loading/error yang jujur.
 * Efek tidak pernah menelan kegagalan: error disimpan dan ditampilkan pemanggil.
 */
export function useApiQuery<T>(path: string): ApiQueryState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    api
      .get<T>(path)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(
          err instanceof ApiError
            ? err
            : new ApiError(0, 'Terjadi kesalahan tak terduga.', 'unknown', err)
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [path, tick]);

  const refresh = useCallback(() => setTick((value) => value + 1), []);

  return { data, error, loading, refresh };
}
