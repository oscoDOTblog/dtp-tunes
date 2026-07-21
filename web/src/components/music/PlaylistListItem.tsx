import Link from "next/link";
import type { Playlist } from "@/lib/types";
import { PlaylistCover } from "@/components/music/PlaylistCover";
import { cn } from "@/lib/utils";

export function PlaylistListItem({ playlist, active }: { playlist: Playlist; active?: boolean }) {
  return (
    <Link
      href={`/playlist/${playlist.id}`}
      className={cn(
        "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-bg-hover",
        active ? "bg-bg-hover text-accent" : "text-fg-secondary hover:text-fg-primary"
      )}
    >
      <PlaylistCover coverArtIds={playlist.coverArtIds} size="sm" alt={playlist.name} />
      <div className="min-w-0">
        <p className="truncate font-medium">{playlist.name}</p>
        <p className="truncate text-xs text-fg-muted">{playlist.songCount} songs</p>
      </div>
    </Link>
  );
}
