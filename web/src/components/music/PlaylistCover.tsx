import Image from "next/image";
import { ListMusic } from "lucide-react";
import { coverUrl } from "@/lib/api";
import { cn } from "@/lib/utils";

interface PlaylistCoverProps {
  coverArtIds?: string[] | null;
  size?: "sm" | "md" | "lg";
  className?: string;
  alt?: string;
}

const SIZE_CLASSES = {
  sm: "h-9 w-9",
  md: "h-12 w-12",
  lg: "h-28 w-28 sm:h-40 sm:w-40",
} as const;

const TILE_SIZES = {
  sm: 40,
  md: 56,
  lg: 160,
} as const;

/** Square mosaic of up to four album covers; falls back to a playlist icon. */
export function PlaylistCover({
  coverArtIds,
  size = "md",
  className,
  alt = "Playlist cover",
}: PlaylistCoverProps) {
  const covers = (coverArtIds ?? []).filter(Boolean).slice(0, 4);
  const box = SIZE_CLASSES[size];
  const tileSize = TILE_SIZES[size];

  if (covers.length === 0) {
    return (
      <div
        className={cn(
          "flex flex-shrink-0 items-center justify-center overflow-hidden rounded-md bg-bg-elevated-2 text-fg-muted",
          box,
          className
        )}
        aria-label={alt}
      >
        <ListMusic size={size === "lg" ? 36 : 16} />
      </div>
    );
  }

  if (covers.length === 1) {
    return (
      <div className={cn("relative flex-shrink-0 overflow-hidden rounded-md bg-bg-elevated-2", box, className)}>
        <Image src={coverUrl(covers[0], tileSize * 2)} alt={alt} fill sizes={`${tileSize}px`} className="object-cover" unoptimized />
      </div>
    );
  }

  const tiles = covers.length === 2 || covers.length === 3 ? covers.slice(0, 2) : covers.slice(0, 4);

  return (
    <div
      className={cn("grid flex-shrink-0 overflow-hidden rounded-md bg-bg-elevated-2", box, className, {
        "grid-cols-2 grid-rows-1": tiles.length === 2,
        "grid-cols-2 grid-rows-2": tiles.length === 4,
      })}
      aria-label={alt}
    >
      {tiles.map((coverId) => (
        <div key={coverId} className="relative min-h-0 min-w-0">
          <Image
            src={coverUrl(coverId, tileSize)}
            alt=""
            fill
            sizes={`${Math.ceil(tileSize / 2)}px`}
            className="object-cover"
            unoptimized
          />
        </div>
      ))}
    </div>
  );
}
