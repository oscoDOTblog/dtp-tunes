"use client";

import Image from "next/image";
import { Pause, Play, Heart, MoreHorizontal } from "lucide-react";
import type { Song } from "@/lib/types";
import { coverUrl } from "@/lib/api";
import { formatDuration } from "@/lib/format";
import { usePlayerStore } from "@/store/playerStore";
import { cn } from "@/lib/utils";

interface SongRowProps {
  song: Song;
  index: number;
  queue: Song[];
  showAlbum?: boolean;
  showCover?: boolean;
  onToggleStar?: (song: Song) => void;
}

export function SongRow({ song, index, queue, showAlbum = true, showCover = false, onToggleStar }: SongRowProps) {
  const currentSong = usePlayerStore((s) => s.currentSong());
  const isPlaying = usePlayerStore((s) => s.isPlaying);
  const playQueue = usePlayerStore((s) => s.playQueue);
  const togglePlay = usePlayerStore((s) => s.togglePlay);

  const isCurrent = currentSong?.id === song.id;

  function handlePlay() {
    if (isCurrent) {
      togglePlay();
    } else {
      playQueue(queue, index);
    }
  }

  return (
    <div
      className={cn(
        "group grid grid-cols-[2rem_1fr_auto] sm:grid-cols-[2rem_1fr_10rem_3rem_2rem] items-center gap-4 rounded-lg px-3 py-2 hover:bg-bg-hover",
        isCurrent && "text-accent"
      )}
    >
      <button
        onClick={handlePlay}
        className="flex h-6 w-6 items-center justify-center text-fg-secondary hover:text-fg-primary"
        aria-label={isCurrent && isPlaying ? "Pause" : "Play"}
      >
        {isCurrent && isPlaying ? (
          <Pause size={16} className="text-accent" fill="currentColor" />
        ) : (
          <>
            <span className={cn("text-sm group-hover:hidden", isCurrent && "text-accent")}>{index + 1}</span>
            <Play size={14} className="hidden group-hover:block" fill="currentColor" />
          </>
        )}
      </button>

      <div className="flex min-w-0 items-center gap-3">
        {showCover && (
          <div className="relative h-10 w-10 flex-shrink-0 overflow-hidden rounded bg-bg-elevated-2">
            <Image src={coverUrl(song.coverArtId, 80)} alt={song.title} fill sizes="40px" className="object-cover" unoptimized />
          </div>
        )}
        <div className="min-w-0">
          <p className={cn("truncate text-sm font-medium", isCurrent ? "text-accent" : "text-fg-primary")}>{song.title}</p>
          <p className="truncate text-xs text-fg-secondary">{song.artistName ?? "Unknown Artist"}</p>
        </div>
      </div>

      {showAlbum ? (
        <p className="hidden truncate text-sm text-fg-secondary sm:block">{song.albumName ?? ""}</p>
      ) : (
        <span className="hidden sm:block" />
      )}

      <button
        onClick={() => onToggleStar?.(song)}
        className={cn(
          "hidden items-center justify-center text-fg-secondary hover:text-accent sm:flex",
          song.starred && "text-accent",
          !song.starred && "opacity-0 group-hover:opacity-100"
        )}
        aria-label={song.starred ? "Unstar" : "Star"}
      >
        <Heart size={16} fill={song.starred ? "currentColor" : "none"} />
      </button>

      <div className="flex items-center justify-end gap-2 text-xs text-fg-secondary">
        <span>{formatDuration(song.duration)}</span>
        <MoreHorizontal size={16} className="hidden opacity-0 group-hover:opacity-100 sm:block" />
      </div>
    </div>
  );
}
