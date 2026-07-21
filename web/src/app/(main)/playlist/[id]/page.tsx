"use client";

import { use, useState } from "react";
import { Play, Pencil, Trash2, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useFetch } from "@/lib/useFetch";
import { SongRow } from "@/components/music/SongRow";
import { PlaylistCover } from "@/components/music/PlaylistCover";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/components/ui/ToastProvider";
import { api, ApiError } from "@/lib/api";
import { formatAlbumDuration } from "@/lib/format";
import { usePlayerStore } from "@/store/playerStore";
import { usePlaylistsRefresh } from "@/store/playlistsRefreshStore";
import type { Playlist, Song } from "@/lib/types";

interface PlaylistDetail {
  playlist: Playlist;
  songs: Song[];
}

export default function PlaylistPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const toast = useToast();
  const { data, isLoading, error, refetch } = useFetch<PlaylistDetail>(`/api/playlists/${id}`, [id]);
  const playQueue = usePlayerStore((s) => s.playQueue);
  const bumpPlaylists = usePlaylistsRefresh((s) => s.bump);
  const [renaming, setRenaming] = useState(false);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [removingIndex, setRemovingIndex] = useState<number | null>(null);

  const mutating = saving || deleting || removingIndex !== null;

  async function saveName() {
    setSaving(true);
    try {
      await api.patch(`/api/playlists/${id}`, { name });
      setRenaming(false);
      refetch();
      bumpPlaylists();
      toast.success("Playlist renamed");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to rename playlist");
    } finally {
      setSaving(false);
    }
  }

  async function deletePlaylist() {
    setDeleting(true);
    try {
      await api.delete(`/api/playlists/${id}`);
      bumpPlaylists();
      toast.success("Playlist deleted");
      router.push("/library");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to delete playlist");
      setDeleting(false);
    }
  }

  async function removeSong(index: number) {
    setRemovingIndex(index);
    try {
      await api.patch(`/api/playlists/${id}`, { songIndexesToRemove: [index] });
      toast.success("Removed from playlist");
      refetch();
      bumpPlaylists();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to remove song");
    } finally {
      setRemovingIndex(null);
    }
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <Skeleton className="h-40 w-full rounded-2xl" />
      </div>
    );
  }
  if (error || !data) return <ErrorState message={error ?? "Playlist not found"} onRetry={refetch} />;

  const { playlist, songs } = data;

  return (
    <div className="flex flex-col gap-8 p-6 pb-32">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
        <PlaylistCover coverArtIds={playlist.coverArtIds} size="lg" alt={playlist.name} />
        <div className="flex min-w-0 flex-1 flex-col gap-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-fg-secondary">Playlist</p>
          {renaming ? (
            <div className="flex max-w-md items-center gap-2">
              <Input value={name} onChange={(e) => setName(e.target.value)} autoFocus disabled={saving} />
              <Button size="sm" onClick={saveName} disabled={saving || !name.trim()}>
                {saving && <Loader2 size={14} className="animate-spin" />}
                {saving ? "Saving…" : "Save"}
              </Button>
            </div>
          ) : (
            <h1 className="text-3xl font-bold text-fg-primary sm:text-4xl">{playlist.name}</h1>
          )}
          <p className="text-sm text-fg-secondary">
            {playlist.songCount} songs · {formatAlbumDuration(playlist.duration)}
          </p>
          <div className="flex items-center gap-2">
            <Button onClick={() => playQueue(songs, 0)} disabled={songs.length === 0}>
              <Play size={16} fill="currentColor" /> Play
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={mutating}
              onClick={() => {
                setName(playlist.name);
                setRenaming(true);
              }}
            >
              <Pencil size={14} /> Rename
            </Button>
            <Button variant="secondary" size="sm" onClick={deletePlaylist} disabled={mutating}>
              {deleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
              {deleting ? "Deleting…" : "Delete"}
            </Button>
          </div>
        </div>
      </div>

      {songs.length === 0 ? (
        <EmptyState title="This playlist is empty" description="Add songs from any album or search result." />
      ) : (
        <div className="flex flex-col">
          {songs.map((song, index) => (
            <div key={`${song.id}-${index}`} className="group flex items-center">
              <div className="flex-1">
                <SongRow song={song} index={index} queue={songs} showAlbum showCover />
              </div>
              <button
                onClick={() => removeSong(index)}
                disabled={mutating}
                className={
                  removingIndex === index
                    ? "mr-2 block text-fg-muted"
                    : "mr-2 hidden text-fg-muted hover:text-danger disabled:pointer-events-none disabled:opacity-40 group-hover:block"
                }
                aria-label="Remove from playlist"
              >
                {removingIndex === index ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
