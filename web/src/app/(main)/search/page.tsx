"use client";

import { useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Search as SearchIcon } from "lucide-react";
import { useFetch } from "@/lib/useFetch";
import { AlbumCard } from "@/components/music/AlbumCard";
import { ArtistCard } from "@/components/music/ArtistCard";
import { SongRow } from "@/components/music/SongRow";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Input } from "@/components/ui/Input";
import type { SearchResult } from "@/lib/types";

export default function SearchPage() {
  const params = useSearchParams();
  const router = useRouter();
  const initialQuery = params.get("q") ?? "";
  const [query, setQuery] = useState(initialQuery);

  const path = initialQuery ? `/api/search?q=${encodeURIComponent(initialQuery)}` : null;
  const { data, isLoading, error, refetch } = useFetch<SearchResult>(path, [initialQuery]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    router.push(`/search?q=${encodeURIComponent(query.trim())}`);
  }

  return (
    <div className="flex flex-col gap-8 p-6 pb-32">
      <form onSubmit={handleSubmit} className="max-w-md">
        <div className="relative">
          <SearchIcon size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-fg-muted" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search artists, albums, songs"
            className="pl-10"
          />
        </div>
      </form>

      {!initialQuery && <EmptyState icon={<SearchIcon size={40} />} title="Search your library" description="Find artists, albums, and songs." />}

      {isLoading && <p className="text-sm text-fg-secondary">Searching…</p>}
      {error && <ErrorState message={error} onRetry={refetch} />}

      {data && (
        <>
          {data.artists.length > 0 && (
            <section>
              <h2 className="mb-4 text-lg font-semibold text-fg-primary">Artists</h2>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
                {data.artists.map((artist) => (
                  <ArtistCard key={artist.id} artist={artist} />
                ))}
              </div>
            </section>
          )}

          {data.albums.length > 0 && (
            <section>
              <h2 className="mb-4 text-lg font-semibold text-fg-primary">Albums</h2>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
                {data.albums.map((album) => (
                  <AlbumCard key={album.id} album={album} />
                ))}
              </div>
            </section>
          )}

          {data.songs.length > 0 && (
            <section>
              <h2 className="mb-4 text-lg font-semibold text-fg-primary">Songs</h2>
              <div className="flex flex-col">
                {data.songs.map((song, index) => (
                  <SongRow key={song.id} song={song} index={index} queue={data.songs} showCover />
                ))}
              </div>
            </section>
          )}

          {data.artists.length === 0 && data.albums.length === 0 && data.songs.length === 0 && (
            <EmptyState title="No results" description={`Nothing matched "${initialQuery}".`} />
          )}
        </>
      )}
    </div>
  );
}
