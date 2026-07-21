"use client";

import { X, ListMusic } from "lucide-react";
import Image from "next/image";
import { usePlayerStore } from "@/store/playerStore";
import { coverUrl } from "@/lib/api";
import { formatDuration } from "@/lib/format";
import { EmptyState } from "@/components/ui/EmptyState";
import { cn } from "@/lib/utils";

export default function QueuePage() {
  const queue = usePlayerStore((s) => s.queue);
  const currentIndex = usePlayerStore((s) => s.currentIndex);
  const jumpTo = usePlayerStore((s) => s.jumpTo);
  const removeFromQueue = usePlayerStore((s) => s.removeFromQueue);

  if (queue.length === 0) {
    return (
      <div className="p-6">
        <EmptyState icon={<ListMusic size={40} />} title="Queue is empty" description="Play a song or album to start building your queue." />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6 pb-32">
      <h1 className="text-2xl font-bold text-fg-primary">Play Queue</h1>
      <div className="flex flex-col">
        {queue.map((song, index) => (
          <div
            key={`${song.id}-${index}`}
            className={cn(
              "group flex items-center gap-3 rounded-lg px-3 py-2 hover:bg-bg-hover cursor-pointer",
              index === currentIndex && "text-accent"
            )}
            onClick={() => jumpTo(index)}
          >
            <div className="relative h-10 w-10 flex-shrink-0 overflow-hidden rounded bg-bg-elevated-2">
              <Image src={coverUrl(song.coverArtId, 80)} alt={song.title} fill sizes="40px" className="object-cover" unoptimized />
            </div>
            <div className="min-w-0 flex-1">
              <p className={cn("truncate text-sm font-medium", index === currentIndex ? "text-accent" : "text-fg-primary")}>
                {song.title}
              </p>
              <p className="truncate text-xs text-fg-secondary">{song.artistName ?? "Unknown Artist"}</p>
            </div>
            <span className="text-xs text-fg-secondary">{formatDuration(song.duration)}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                removeFromQueue(index);
              }}
              className="text-fg-muted opacity-0 hover:text-danger group-hover:opacity-100"
              aria-label="Remove from queue"
            >
              <X size={16} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
