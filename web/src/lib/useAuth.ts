"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { User } from "@/lib/types";

interface AuthState {
  user: User | null;
  isLoading: boolean;
  error: string | null;
}

export function useAuth() {
  const router = useRouter();
  const [state, setState] = useState<AuthState>({ user: null, isLoading: true, error: null });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;

    api
      .get<User>("/api/auth/me")
      .then((user) => {
        if (!cancelled) setState({ user, isLoading: false, error: null });
      })
      .catch((err) => {
        if (cancelled) return;
        const message = err instanceof ApiError ? err.message : "Failed to load session";
        setState({ user: null, isLoading: false, error: message });
      });

    return () => {
      cancelled = true;
    };
  }, [tick]);

  const refresh = useCallback(() => {
    setState((s) => ({ ...s, isLoading: true }));
    setTick((t) => t + 1);
  }, []);

  const logout = useCallback(async () => {
    await api.post("/api/auth/logout");
    setState({ user: null, isLoading: false, error: null });
    router.push("/login");
  }, [router]);

  return { ...state, refresh, logout };
}
