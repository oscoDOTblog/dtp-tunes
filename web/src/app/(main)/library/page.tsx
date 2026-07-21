"use client";

import { useState } from "react";
import { useFetch } from "@/lib/useFetch";
import { AlbumCard } from "@/components/music/AlbumCard";
import { ArtistCard } from "@/components/music/ArtistCard";
import { SongRow } from "@/components/music/SongRow";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { cn } from "@/lib/utils";
import type { Album, Artist, Song } from "@/lib/types";
import { Library as LibraryIcon } from "lucide-react";

type Tab = "albums" | "artists" | "starred";

const tabs: { id: Tab; label: string }[] = [
  { id: "albums", label: "Albums" },
  { id: "artists", label: "Artists" },
  { id: "starred", label: "Liked Songs" },
];

export default function LibraryPage() {
  const [tab, setTab] = useState<Tab>("albums");

  const albums = useFetch<Album[]>(tab === "albums" ? "/api/albums?sort=name&limit=200" : null);
  const artists = useFetch<Artist[]>(tab === "artists" ? "/api/artists" : null);
  const starred = useFetch<Song[]>(tab === "starred" ? "/api/starred/songs" : null);

  return (
    <div className="flex flex-col gap-6 p-6 pb-32">
      <h1 className="text-2xl font-bold text-fg-primary">Your Library</h1>

      <div className="flex gap-2 border-b border-border-subtle">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
              tab === t.id ? "border-accent text-fg-primary" : "border-transparent text-fg-secondary hover:text-fg-primary"
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "albums" && (
        <>
          {albums.isLoading && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
              {Array.from({ length: 12 }).map((_, i) => (
                <Skeleton key={i} className="aspect-square" />
              ))}
            </div>
          )}
          {albums.error && <ErrorState message={albums.error} onRetry={albums.refetch} />}
          {albums.data && albums.data.length === 0 && <EmptyState icon={<LibraryIcon size={40} />} title="No albums yet" description="Run a scan from Settings to import your music." />}
          {albums.data && albums.data.length > 0 && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
              {albums.data.map((album) => (
                <AlbumCard key={album.id} album={album} />
              ))}
            </div>
          )}
        </>
      )}

      {tab === "artists" && (
        <>
          {artists.isLoading && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
              {Array.from({ length: 12 }).map((_, i) => (
                <Skeleton key={i} className="aspect-square rounded-full" />
              ))}
            </div>
          )}
          {artists.error && <ErrorState message={artists.error} onRetry={artists.refetch} />}
          {artists.data && artists.data.length === 0 && <EmptyState title="No artists yet" description="Run a scan from Settings to import your music." />}
          {artists.data && artists.data.length > 0 && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
              {artists.data.map((artist) => (
                <ArtistCard key={artist.id} artist={artist} />
              ))}
            </div>
          )}
        </>
      )}

      {tab === "starred" && (
        <>
          {starred.isLoading && <p className="text-sm text-fg-secondary">Loading…</p>}
          {starred.error && <ErrorState message={starred.error} onRetry={starred.refetch} />}
          {starred.data && starred.data.length === 0 && <EmptyState title="No liked songs" description="Star songs to save them here." />}
          {starred.data && starred.data.length > 0 && (
            <div className="flex flex-col">
              {starred.data.map((song, index) => (
                <SongRow key={song.id} song={song} index={index} queue={starred.data!} showCover />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
