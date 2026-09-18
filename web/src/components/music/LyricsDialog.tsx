"use client";

import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { FileUp, Loader2, Trash2, X } from "lucide-react";
import type { Song } from "@/lib/types";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/ToastProvider";

const MAX_LYRICS_BYTES = 1024 * 1024;

interface LyricsResponse {
  lyrics: string | null;
  hasLyrics: boolean;
}

interface LyricsDialogProps {
  song: Song;
  onClose: () => void;
}

export function LyricsDialog({ song, onClose }: LyricsDialogProps) {
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [lyrics, setLyrics] = useState("");
  const [savedLyrics, setSavedLyrics] = useState("");
  const [hasSavedLyrics, setHasSavedLyrics] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dirty = lyrics !== savedLyrics;

  useEffect(() => {
    let cancelled = false;
    api
      .get<LyricsResponse>(`/api/songs/${song.id}/lyrics`)
      .then((response) => {
        if (cancelled) return;
        const value = response.lyrics ?? "";
        setLyrics(value);
        setSavedLyrics(value);
        setHasSavedLyrics(response.hasLyrics);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load lyrics");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [song.id]);

  function requestClose() {
    if (dirty && !window.confirm("Discard your unsaved lyrics changes?")) return;
    onClose();
  }

  async function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.size > MAX_LYRICS_BYTES) {
      toast.error("Lyrics file must be 1 MiB or smaller");
      return;
    }
    if (dirty && !window.confirm("Replace your unsaved text with the selected file?")) return;
    try {
      const buffer = await file.arrayBuffer();
      const value = new TextDecoder("utf-8", { fatal: true }).decode(buffer).replace(/^\uFEFF/, "");
      setLyrics(value.replace(/\r\n?/g, "\n"));
      setError(null);
    } catch {
      toast.error("Lyrics file must contain valid UTF-8 text");
    }
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const response = await api.put<LyricsResponse>(`/api/songs/${song.id}/lyrics`, { lyrics });
      const value = response.lyrics ?? "";
      setLyrics(value);
      setSavedLyrics(value);
      setHasSavedLyrics(response.hasLyrics);
      toast.success("Lyrics saved");
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save lyrics");
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!window.confirm("Delete the lyrics for this song?")) return;
    setSaving(true);
    setError(null);
    try {
      await api.delete<LyricsResponse>(`/api/songs/${song.id}/lyrics`);
      setLyrics("");
      setSavedLyrics("");
      setHasSavedLyrics(false);
      toast.success("Lyrics deleted");
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete lyrics");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 sm:items-center sm:p-6" onClick={requestClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="lyrics-dialog-title"
        className="flex max-h-[92vh] w-full max-w-3xl flex-col rounded-t-2xl border border-border-subtle bg-bg-elevated shadow-2xl sm:rounded-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b border-border-subtle px-5 py-4">
          <div className="min-w-0">
            <h2 id="lyrics-dialog-title" className="truncate text-lg font-semibold text-fg-primary">Edit lyrics</h2>
            <p className="truncate text-sm text-fg-secondary">{song.title} · {song.artistName ?? "Unknown Artist"}</p>
          </div>
          <button type="button" onClick={requestClose} className="text-fg-secondary hover:text-fg-primary" aria-label="Close">
            <X size={20} />
          </button>
        </div>

        <div className="flex min-h-0 flex-1 flex-col gap-3 p-5">
          <input ref={fileRef} type="file" accept=".txt,text/plain" className="hidden" onChange={chooseFile} />
          <div className="flex items-center justify-between gap-3">
            <Button variant="secondary" size="sm" onClick={() => fileRef.current?.click()} disabled={loading || saving}>
              <FileUp size={15} /> Load .txt file
            </Button>
            <span className="text-xs text-fg-muted">UTF-8 · 1 MiB maximum</span>
          </div>
          {loading ? (
            <div className="flex min-h-80 items-center justify-center text-fg-secondary"><Loader2 className="animate-spin" /></div>
          ) : (
            <textarea
              value={lyrics}
              onChange={(event) => setLyrics(event.target.value)}
              placeholder="Paste the song lyrics here…"
              spellCheck
              autoFocus
              className="min-h-80 flex-1 resize-y whitespace-pre-wrap rounded-xl border border-border-subtle bg-bg-base p-4 font-mono text-sm leading-relaxed text-fg-primary outline-none transition-colors placeholder:text-fg-muted focus:border-accent"
            />
          )}
          {error && <p role="alert" className="text-sm text-danger">{error}</p>}
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-border-subtle px-5 py-4">
          <Button variant="ghost" size="sm" onClick={remove} disabled={loading || saving || !hasSavedLyrics} className="text-danger">
            <Trash2 size={15} /> Delete
          </Button>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={requestClose} disabled={saving}>Cancel</Button>
            <Button size="sm" onClick={save} disabled={loading || saving || !dirty}>
              {saving && <Loader2 size={14} className="animate-spin" />}
              {saving ? "Saving…" : "Save lyrics"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
