"use client";

import { use, useState } from "react";
import { Play, Pencil, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useFetch } from "@/lib/useFetch";
import { SongRow } from "@/components/music/SongRow";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api } from "@/lib/api";
import { formatAlbumDuration } from "@/lib/format";
import { usePlayerStore } from "@/store/playerStore";
import type { Playlist, Song } from "@/lib/types";

interface PlaylistDetail {
  playlist: Playlist;
  songs: Song[];
}

export default function PlaylistPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { data, isLoading, error, refetch } = useFetch<PlaylistDetail>(`/api/playlists/${id}`, [id]);
  const playQueue = usePlayerStore((s) => s.playQueue);
  const [renaming, setRenaming] = useState(false);
  const [name, setName] = useState("");

  async function saveName() {
    await api.patch(`/api/playlists/${id}`, { name });
    setRenaming(false);
    refetch();
  }

  async function deletePlaylist() {
    await api.delete(`/api/playlists/${id}`);
    router.push("/library");
  }

  async function removeSong(index: number) {
    await api.patch(`/api/playlists/${id}`, { songIndexesToRemove: [index] });
    refetch();
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
      <div className="flex flex-col gap-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-fg-secondary">Playlist</p>
        {renaming ? (
          <div className="flex max-w-md items-center gap-2">
            <Input value={name} onChange={(e) => setName(e.target.value)} autoFocus />
            <Button size="sm" onClick={saveName}>
              Save
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
            onClick={() => {
              setName(playlist.name);
              setRenaming(true);
            }}
          >
            <Pencil size={14} /> Rename
          </Button>
          <Button variant="secondary" size="sm" onClick={deletePlaylist}>
            <Trash2 size={14} /> Delete
          </Button>
        </div>
      </div>

      {songs.length === 0 ? (
        <EmptyState title="This playlist is empty" description="Add songs from any album or search result." />
      ) : (
        <div className="flex flex-col">
          {songs.map((song, index) => (
            <div key={song.id} className="group flex items-center">
              <div className="flex-1">
                <SongRow song={song} index={index} queue={songs} showAlbum showCover />
              </div>
              <button
                onClick={() => removeSong(index)}
                className="mr-2 hidden text-fg-muted hover:text-danger group-hover:block"
                aria-label="Remove from playlist"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
