"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastTone = "success" | "info" | "error";

interface ToastItem {
  id: string;
  message: string;
  tone: ToastTone;
}

interface ToastApi {
  success: (message: string) => void;
  info: (message: string) => void;
  error: (message: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

const TONE_CLASSES: Record<ToastTone, string> = {
  success: "border-accent/40 bg-bg-elevated text-fg-primary",
  info: "border-border-subtle bg-bg-elevated text-fg-primary",
  error: "border-danger/50 bg-bg-elevated text-fg-primary",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const push = useCallback(
    (message: string, tone: ToastTone) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      setToasts((current) => [...current, { id, message, tone }]);
      window.setTimeout(() => dismiss(id), 3200);
    },
    [dismiss]
  );

  const api = useMemo<ToastApi>(
    () => ({
      success: (message) => push(message, "success"),
      info: (message) => push(message, "info"),
      error: (message) => push(message, "error"),
    }),
    [push]
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        aria-live="polite"
        aria-relevant="additions"
        className="pointer-events-none fixed bottom-24 right-4 z-[60] flex w-[min(22rem,calc(100vw-2rem))] flex-col gap-2"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={cn(
              "pointer-events-auto flex items-start gap-3 rounded-xl border px-4 py-3 text-sm shadow-2xl",
              TONE_CLASSES[toast.tone]
            )}
          >
            <p className="flex-1 leading-snug">{toast.message}</p>
            <button
              type="button"
              onClick={() => dismiss(toast.id)}
              className="text-fg-muted hover:text-fg-primary"
              aria-label="Dismiss notification"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return ctx;
}
