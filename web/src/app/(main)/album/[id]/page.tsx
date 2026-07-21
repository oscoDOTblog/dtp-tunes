"use client";

import { use } from "react";
import Image from "next/image";
import Link from "next/link";
import { Play } from "lucide-react";
import { useFetch } from "@/lib/useFetch";
import { SongRow } from "@/components/music/SongRow";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { Button } from "@/components/ui/Button";
import { coverUrl, api } from "@/lib/api";
import { formatAlbumDuration } from "@/lib/format";
import { usePlayerStore } from "@/store/playerStore";
import type { Album, Song } from "@/lib/types";

interface AlbumDetail {
  album: Album;
  songs: Song[];
}

export default function AlbumPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data, isLoading, error, refetch } = useFetch<AlbumDetail>(`/api/albums/${id}`, [id]);
  const playQueue = usePlayerStore((s) => s.playQueue);

  async function toggleStar(song: Song) {
    if (song.starred) await api.delete(`/api/songs/${song.id}/star`);
    else await api.post(`/api/songs/${song.id}/star`);
    refetch();
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    );
  }
  if (error || !data) return <ErrorState message={error ?? "Album not found"} onRetry={refetch} />;

  const { album, songs } = data;

  return (
    <div className="flex flex-col gap-8 p-6 pb-32">
      <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-end">
        <div className="relative h-48 w-48 flex-shrink-0 overflow-hidden rounded-xl bg-bg-elevated-2 shadow-2xl">
          <Image src={coverUrl(album.coverArtId, 500)} alt={album.name} fill sizes="200px" className="object-cover" unoptimized />
        </div>
        <div className="text-center sm:text-left">
          <p className="text-xs font-semibold uppercase tracking-wide text-fg-secondary">Album</p>
          <h1 className="text-3xl font-bold text-fg-primary sm:text-4xl">{album.name}</h1>
          <p className="mt-2 text-sm text-fg-secondary">
            {album.artistId ? (
              <Link href={`/artist/${album.artistId}`} className="font-medium text-fg-primary hover:underline">
                {album.artistName}
              </Link>
            ) : (
              album.artistName ?? "Unknown Artist"
            )}
            {album.year ? ` · ${album.year}` : ""} · {album.songCount} songs · {formatAlbumDuration(album.duration)}
          </p>
          <Button className="mt-4" onClick={() => playQueue(songs, 0)}>
            <Play size={16} fill="currentColor" /> Play
          </Button>
        </div>
      </div>

      <div className="flex flex-col">
        {songs.map((song, index) => (
          <SongRow key={song.id} song={song} index={index} queue={songs} showAlbum={false} onToggleStar={toggleStar} />
        ))}
      </div>
    </div>
  );
}
