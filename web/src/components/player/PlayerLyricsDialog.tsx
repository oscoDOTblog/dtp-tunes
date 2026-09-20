"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { Song } from "@/lib/types";

export function PlayerLyricsDialog({ song, onClose }: { song: Song; onClose: () => void }) {
  const [lyrics, setLyrics] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    let cancelled = false;
    api.get<{ lyrics: string | null }>(`/api/songs/${song.id}/lyrics`)
      .then((response) => {
        if (!cancelled) setLyrics(response.lyrics);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load lyrics");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [song.id]);

  useEffect(() => {
    closeRef.current?.focus();
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-[60] flex items-end justify-center bg-black/60 sm:items-center sm:p-6" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="player-lyrics-title"
        className="flex max-h-[92vh] w-full max-w-2xl flex-col rounded-t-2xl border border-border-subtle bg-bg-elevated shadow-2xl sm:rounded-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 border-b border-border-subtle px-5 py-4">
          <div className="min-w-0">
            <h2 id="player-lyrics-title" className="text-lg font-semibold text-fg-primary">Lyrics</h2>
            <p className="truncate text-sm text-fg-secondary">{song.title} · {song.artistName ?? "Unknown Artist"}</p>
          </div>
          <button ref={closeRef} type="button" onClick={onClose} className="text-fg-secondary hover:text-fg-primary" aria-label="Close lyrics">
            <X size={20} />
          </button>
        </div>
        <div className="min-h-48 overflow-y-auto px-5 py-6 text-center text-fg-primary sm:px-10">
          {loading ? (
            <div className="flex justify-center" role="status" aria-label="Loading lyrics"><Loader2 className="animate-spin" /></div>
          ) : error ? (
            <p role="alert" className="text-sm text-danger">{error}</p>
          ) : lyrics?.trim() ? (
            <p className="whitespace-pre-wrap break-words text-base leading-8">{lyrics}</p>
          ) : (
            <p className="text-sm text-fg-secondary">No lyrics available for this song.</p>
          )}
        </div>
      </div>
    </div>
  );
}
