import Link from "next/link";
import Image from "next/image";
import { Play } from "lucide-react";
import type { Album } from "@/lib/types";
import { coverUrl } from "@/lib/api";

export function AlbumCard({ album }: { album: Album }) {
  return (
    <Link
      href={`/album/${album.id}`}
      className="group relative flex flex-col gap-3 rounded-xl bg-bg-elevated p-4 transition-colors duration-150 hover:bg-bg-elevated-2"
    >
      <div className="relative aspect-square overflow-hidden rounded-lg bg-bg-elevated-2 shadow-lg">
        <Image
          src={coverUrl(album.coverArtId, 300)}
          alt={album.name}
          fill
          sizes="200px"
          className="object-cover"
          unoptimized
        />
        <div className="absolute bottom-2 right-2 flex h-11 w-11 translate-y-2 items-center justify-center rounded-full bg-accent text-black opacity-0 shadow-xl transition-all duration-150 group-hover:translate-y-0 group-hover:opacity-100">
          <Play size={18} fill="black" />
        </div>
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-fg-primary">{album.name}</p>
        <p className="truncate text-xs text-fg-secondary">
          {album.year ? `${album.year} · ` : ""}
          {album.artistName ?? "Unknown Artist"}
        </p>
      </div>
    </Link>
  );
}
