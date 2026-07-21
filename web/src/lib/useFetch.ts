"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";

interface FetchState<T> {
  data: T | null;
  isLoading: boolean;
  error: string | null;
}

/** Minimal client-side data hook: fetch on mount / dependency change, expose refetch. */
export function useFetch<T>(path: string | null, deps: unknown[] = []): FetchState<T> & { refetch: () => void } {
  const [state, setState] = useState<FetchState<T>>({ data: null, isLoading: path !== null, error: null });
  const [tick, setTick] = useState(0);
  const depsKey = JSON.stringify(deps);

  useEffect(() => {
    if (path === null) return;
    let cancelled = false;

    api
      .get<T>(path)
      .then((data) => {
        if (!cancelled) setState({ data, isLoading: false, error: null });
      })
      .catch((err) => {
        if (cancelled) return;
        const message = err instanceof ApiError ? err.message : "Failed to load data";
        setState({ data: null, isLoading: false, error: message });
      });

    return () => {
      cancelled = true;
    };
  }, [path, depsKey, tick]);

  function refetch() {
    setState((s) => ({ ...s, isLoading: true, error: null }));
    setTick((t) => t + 1);
  }

  return { ...state, refetch };
}
