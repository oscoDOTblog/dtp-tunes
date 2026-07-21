"use client";

import Image from "next/image";
import { X, Play, Pause, SkipBack, SkipForward, Shuffle, Repeat, Repeat1, Heart } from "lucide-react";
import { usePlayerStore } from "@/store/playerStore";
import { coverUrl } from "@/lib/api";
import { formatDuration } from "@/lib/format";
import { seekTo } from "@/lib/audioController";
import { IconButton } from "@/components/ui/IconButton";
import { Slider } from "@/components/ui/Slider";
import { cn } from "@/lib/utils";

export function NowPlayingSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const currentSong = usePlayerStore((s) => s.currentSong());
  const isPlaying = usePlayerStore((s) => s.isPlaying);
  const currentTime = usePlayerStore((s) => s.currentTime);
  const duration = usePlayerStore((s) => s.duration);
  const shuffle = usePlayerStore((s) => s.shuffle);
  const repeat = usePlayerStore((s) => s.repeat);

  const togglePlay = usePlayerStore((s) => s.togglePlay);
  const next = usePlayerStore((s) => s.next);
  const previous = usePlayerStore((s) => s.previous);
  const toggleShuffle = usePlayerStore((s) => s.toggleShuffle);
  const cycleRepeat = usePlayerStore((s) => s.cycleRepeat);
  const setCurrentTime = usePlayerStore((s) => s.setCurrentTime);

  if (!open || !currentSong) return null;

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-bg-base p-6">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-fg-secondary">Now Playing</span>
        <button onClick={onClose} aria-label="Close" className="text-fg-secondary hover:text-fg-primary">
          <X size={22} />
        </button>
      </div>

      <div className="flex flex-1 flex-col items-center justify-center gap-8">
        <div className="relative aspect-square w-full max-w-sm overflow-hidden rounded-2xl bg-bg-elevated-2 shadow-2xl">
          <Image src={coverUrl(currentSong.coverArtId, 600)} alt={currentSong.title} fill sizes="400px" className="object-cover" unoptimized />
        </div>

        <div className="w-full max-w-sm text-center">
          <p className="truncate text-xl font-bold text-fg-primary">{currentSong.title}</p>
          <p className="truncate text-sm text-fg-secondary">{currentSong.artistName ?? "Unknown Artist"}</p>
        </div>

        <div className="w-full max-w-sm">
          <Slider
            min={0}
            max={duration || 0}
            value={Math.min(currentTime, duration || 0)}
            onChange={(e) => {
              const value = Number(e.target.value);
              setCurrentTime(value);
              seekTo(value);
            }}
            className="w-full"
            aria-label="Seek"
          />
          <div className="mt-1 flex justify-between text-xs text-fg-muted">
            <span>{formatDuration(currentTime)}</span>
            <span>{formatDuration(duration)}</span>
          </div>
        </div>

        <div className="flex items-center gap-6">
          <IconButton active={shuffle} onClick={toggleShuffle} aria-label="Shuffle">
            <Shuffle size={20} />
          </IconButton>
          <IconButton size="lg" onClick={previous} aria-label="Previous">
            <SkipBack size={26} />
          </IconButton>
          <IconButton size="lg" onClick={togglePlay} className="bg-fg-primary text-bg-base h-16 w-16" aria-label="Play/Pause">
            {isPlaying ? <Pause size={28} fill="currentColor" /> : <Play size={28} fill="currentColor" />}
          </IconButton>
          <IconButton size="lg" onClick={next} aria-label="Next">
            <SkipForward size={26} />
          </IconButton>
          <IconButton active={repeat !== "off"} onClick={cycleRepeat} aria-label="Repeat">
            {repeat === "one" ? <Repeat1 size={20} /> : <Repeat size={20} />}
          </IconButton>
        </div>

        <IconButton className={cn(currentSong.starred && "text-accent")} aria-label="Star">
          <Heart size={20} fill={currentSong.starred ? "currentColor" : "none"} />
        </IconButton>
      </div>
    </div>
  );
}
