"use client";

import { useFetch } from "@/lib/useFetch";
import { AlbumCard } from "@/components/music/AlbumCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import type { Album, Genre } from "@/lib/types";
import { Disc3 } from "lucide-react";
import Link from "next/link";

function AlbumGrid({ albums }: { albums: Album[] }) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
      {albums.map((album) => (
        <AlbumCard key={album.id} album={album} />
      ))}
    </div>
  );
}

function SectionSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="aspect-square" />
      ))}
    </div>
  );
}

export default function HomePage() {
  const recent = useFetch<Album[]>("/api/albums?sort=recent&limit=12");
  const random = useFetch<Album[]>("/api/albums/random?size=12");
  const genres = useFetch<Genre[]>("/api/genres");

  const isEmpty = !recent.isLoading && !recent.error && (recent.data?.length ?? 0) === 0;

  return (
    <div className="flex flex-col gap-10 p-6 pb-32">
      <div>
        <h1 className="mb-1 text-2xl font-bold text-fg-primary">Good listening</h1>
        <p className="text-sm text-fg-secondary">Pick up where your library left off.</p>
      </div>

      {isEmpty && (
        <EmptyState
          icon={<Disc3 size={40} />}
          title="Your library is empty"
          description="Drop audio files into the mounted /music folder, then start a scan from Settings → Library."
          action={
            <Link href="/settings" className="text-sm text-accent hover:underline">
              Go to settings
            </Link>
          }
        />
      )}

      {!isEmpty && (
        <section>
          <h2 className="mb-4 text-lg font-semibold text-fg-primary">Recently added</h2>
          {recent.isLoading && <SectionSkeleton />}
          {recent.error && <ErrorState message={recent.error} onRetry={recent.refetch} />}
          {recent.data && <AlbumGrid albums={recent.data} />}
        </section>
      )}

      {!isEmpty && (
        <section>
          <h2 className="mb-4 text-lg font-semibold text-fg-primary">Picked for you</h2>
          {random.isLoading && <SectionSkeleton />}
          {random.error && <ErrorState message={random.error} onRetry={random.refetch} />}
          {random.data && <AlbumGrid albums={random.data} />}
        </section>
      )}

      {!isEmpty && genres.data && genres.data.length > 0 && (
        <section>
          <h2 className="mb-4 text-lg font-semibold text-fg-primary">Browse by genre</h2>
          <div className="flex flex-wrap gap-2">
            {genres.data.map((genre) => (
              <Link
                key={genre.name}
                href={`/search?q=${encodeURIComponent(genre.name)}`}
                className="rounded-full bg-bg-elevated px-4 py-2 text-sm text-fg-secondary hover:bg-bg-elevated-2 hover:text-fg-primary"
              >
                {genre.name}
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
