"use client";

import { use } from "react";
import Image from "next/image";
import { User, Play } from "lucide-react";
import { useFetch } from "@/lib/useFetch";
import { AlbumCard } from "@/components/music/AlbumCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { Button } from "@/components/ui/Button";
import { coverUrl } from "@/lib/api";
import type { Album, Artist } from "@/lib/types";
import { api } from "@/lib/api";
import { usePlayerStore } from "@/store/playerStore";

interface ArtistDetail {
  artist: Artist;
  albums: Album[];
}

export default function ArtistPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data, isLoading, error, refetch } = useFetch<ArtistDetail>(`/api/artists/${id}`, [id]);
  const playQueue = usePlayerStore((s) => s.playQueue);

  async function playAll() {
    if (!data) return;
    const songs = [];
    for (const album of data.albums) {
      const albumDetail = await api.get<{ songs: import("@/lib/types").Song[] }>(`/api/albums/${album.id}`);
      songs.push(...albumDetail.songs);
    }
    playQueue(songs, 0);
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <Skeleton className="h-48 w-full rounded-2xl" />
      </div>
    );
  }
  if (error || !data) return <ErrorState message={error ?? "Artist not found"} onRetry={refetch} />;

  return (
    <div className="flex flex-col gap-8 p-6 pb-32">
      <div className="flex items-center gap-6">
        <div className="relative h-40 w-40 flex-shrink-0 overflow-hidden rounded-full bg-bg-elevated-2 shadow-2xl">
          {data.artist.coverArtId ? (
            <Image src={coverUrl(data.artist.coverArtId, 400)} alt={data.artist.name} fill className="object-cover" unoptimized />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-fg-muted">
              <User size={48} />
            </div>
          )}
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-fg-secondary">Artist</p>
          <h1 className="text-4xl font-bold text-fg-primary">{data.artist.name}</h1>
          <p className="mt-1 text-sm text-fg-secondary">{data.artist.albumCount} albums</p>
          <Button className="mt-4" onClick={playAll}>
            <Play size={16} fill="currentColor" /> Play all
          </Button>
        </div>
      </div>

      <section>
        <h2 className="mb-4 text-lg font-semibold text-fg-primary">Albums</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {data.albums.map((album) => (
            <AlbumCard key={album.id} album={album} />
          ))}
        </div>
      </section>
    </div>
  );
}
