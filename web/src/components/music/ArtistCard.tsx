import Link from "next/link";
import Image from "next/image";
import { User } from "lucide-react";
import type { Artist } from "@/lib/types";
import { coverUrl } from "@/lib/api";

export function ArtistCard({ artist }: { artist: Artist }) {
  return (
    <Link
      href={`/artist/${artist.id}`}
      className="group flex flex-col gap-3 rounded-xl bg-bg-elevated p-4 transition-colors duration-150 hover:bg-bg-elevated-2"
    >
      <div className="relative aspect-square overflow-hidden rounded-full bg-bg-elevated-2 shadow-lg">
        {artist.coverArtId ? (
          <Image src={coverUrl(artist.coverArtId, 300)} alt={artist.name} fill sizes="200px" className="object-cover" unoptimized />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-fg-muted">
            <User size={40} />
          </div>
        )}
      </div>
      <div className="min-w-0 text-center">
        <p className="truncate text-sm font-semibold text-fg-primary">{artist.name}</p>
        <p className="truncate text-xs text-fg-secondary">Artist</p>
      </div>
    </Link>
  );
}
