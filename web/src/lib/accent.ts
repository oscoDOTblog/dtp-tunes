/**
 * Accent tone preference: a per-device UI setting stored in localStorage and
 * applied as `data-accent` on <html>. CSS variable overrides live in
 * globals.css. "pink" is the default (no attribute needed, but we set it
 * anyway for consistency).
 */

export const ACCENT_STORAGE_KEY = "dtp-tunes-accent";

export const ACCENT_TONES = [
  { id: "pink", label: "Hot pink", swatch: "#ff1493" },
  { id: "green", label: "Green", swatch: "#1db954" },
  { id: "blue", label: "Blue", swatch: "#3b82f6" },
  { id: "purple", label: "Purple", swatch: "#a855f7" },
  { id: "orange", label: "Orange", swatch: "#f97316" },
] as const;

export type AccentTone = (typeof ACCENT_TONES)[number]["id"];

export const DEFAULT_ACCENT: AccentTone = "pink";

export function isAccentTone(value: string | null): value is AccentTone {
  return ACCENT_TONES.some((tone) => tone.id === value);
}

export function getStoredAccent(): AccentTone {
  if (typeof window === "undefined") return DEFAULT_ACCENT;
  const stored = window.localStorage.getItem(ACCENT_STORAGE_KEY);
  return isAccentTone(stored) ? stored : DEFAULT_ACCENT;
}

const listeners = new Set<() => void>();

/** Subscribe to accent changes (for useSyncExternalStore). */
export function subscribeAccent(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getServerAccent(): AccentTone {
  return DEFAULT_ACCENT;
}

export function applyAccent(tone: AccentTone): void {
  document.documentElement.dataset.accent = tone;
  window.localStorage.setItem(ACCENT_STORAGE_KEY, tone);
  listeners.forEach((listener) => listener());
}
