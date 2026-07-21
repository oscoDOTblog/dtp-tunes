"use client";

import { useState } from "react";
import { Check, Plus, X } from "lucide-react";
import { useFetch } from "@/lib/useFetch";
import { api, ApiError } from "@/lib/api";
import { useToast } from "@/components/ui/ToastProvider";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { PlaylistCover } from "@/components/music/PlaylistCover";
import type { Playlist, Song } from "@/lib/types";
import { cn } from "@/lib/utils";

interface SaveToPlaylistDialogProps {
  song: Song;
  open: boolean;
  onClose: () => void;
}

export function SaveToPlaylistDialog({ song, open, onClose }: SaveToPlaylistDialogProps) {
  const toast = useToast();
  const { data: playlists, isLoading, error, refetch } = useFetch<Playlist[]>(
    open ? `/api/playlists?sort=recent&songId=${encodeURIComponent(song.id)}` : null
  );
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [creatingBusy, setCreatingBusy] = useState(false);

  if (!open) return null;

  async function addToPlaylist(playlist: Playlist) {
    if (playlist.containsSong) {
      toast.info(`Already in “${playlist.name}”`);
      return;
    }
    setBusyId(playlist.id);
    try {
      await api.patch(`/api/playlists/${playlist.id}`, { songIdsToAdd: [song.id] });
      toast.success(`Added to “${playlist.name}”`);
      onClose();
    } catch (err) {
      const message =
        err instanceof ApiError && err.status === 409
          ? `Already in “${playlist.name}”`
          : err instanceof ApiError
            ? err.message
            : "Failed to add to playlist";
      toast.error(message);
      refetch();
    } finally {
      setBusyId(null);
    }
  }

  async function createAndAdd() {
    const trimmed = name.trim();
    if (!trimmed) return;
    setCreatingBusy(true);
    try {
      const created = await api.post<Playlist>("/api/playlists", {
        name: trimmed,
        songIds: [song.id],
      });
      toast.success(`Created “${created.name}” and added song`);
      setName("");
      setCreating(false);
      onClose();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to create playlist");
    } finally {
      setCreatingBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 p-0 sm:items-center sm:p-6"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="save-to-playlist-title"
        className="flex max-h-[85vh] w-full max-w-lg flex-col rounded-t-2xl border border-border-subtle bg-bg-elevated shadow-2xl sm:rounded-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border-subtle px-5 py-4">
          <h2 id="save-to-playlist-title" className="text-lg font-semibold text-fg-primary">
            Save to playlist
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-fg-secondary hover:text-fg-primary"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        <div className="scrollbar-none flex-1 overflow-y-auto px-5 py-4">
          <p className="mb-4 truncate text-sm text-fg-secondary">
            Adding <span className="text-fg-primary">{song.title}</span>
          </p>

          {isLoading && <p className="text-sm text-fg-muted">Loading playlists…</p>}
          {error && <p className="text-sm text-danger">{error}</p>}

          {!isLoading && !error && (playlists?.length ?? 0) === 0 && !creating && (
            <p className="mb-4 text-sm text-fg-muted">No playlists yet — create one below.</p>
          )}

          <div className="flex flex-col gap-1">
            {(playlists ?? []).map((playlist) => {
              const disabled = Boolean(playlist.containsSong) || busyId === playlist.id;
              return (
                <button
                  key={playlist.id}
                  type="button"
                  disabled={disabled}
                  onClick={() => addToPlaylist(playlist)}
                  className={cn(
                    "flex items-center gap-3 rounded-xl px-2 py-2 text-left transition-colors",
                    playlist.containsSong
                      ? "cursor-not-allowed opacity-55"
                      : "hover:bg-bg-hover"
                  )}
                >
                  <PlaylistCover coverArtIds={playlist.coverArtIds} size="md" alt={playlist.name} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-fg-primary">{playlist.name}</p>
                    <p className="truncate text-xs text-fg-muted">
                      {playlist.containsSong
                        ? "Already added"
                        : `${playlist.songCount} ${playlist.songCount === 1 ? "song" : "songs"}`}
                    </p>
                  </div>
                  {playlist.containsSong && <Check size={16} className="flex-shrink-0 text-accent" />}
                </button>
              );
            })}
          </div>
        </div>

        <div className="border-t border-border-subtle px-5 py-4">
          {creating ? (
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Playlist name"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === "Enter") createAndAdd();
                  if (e.key === "Escape") setCreating(false);
                }}
                className="flex-1"
              />
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" onClick={() => setCreating(false)} disabled={creatingBusy}>
                  Cancel
                </Button>
                <Button size="sm" onClick={createAndAdd} disabled={!name.trim() || creatingBusy}>
                  Create
                </Button>
              </div>
            </div>
          ) : (
            <Button
              onClick={() => setCreating(true)}
              className="w-full bg-fg-primary text-bg-base hover:bg-fg-primary sm:w-auto"
            >
              <Plus size={16} /> New playlist
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
