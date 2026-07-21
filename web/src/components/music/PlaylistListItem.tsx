import Link from "next/link";
import { ListMusic } from "lucide-react";
import type { Playlist } from "@/lib/types";
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
      <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-md bg-bg-elevated-2">
        <ListMusic size={16} />
      </span>
      <div className="min-w-0">
        <p className="truncate font-medium">{playlist.name}</p>
        <p className="truncate text-xs text-fg-muted">{playlist.songCount} songs</p>
      </div>
    </Link>
  );
}
