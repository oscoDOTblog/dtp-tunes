"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Shuffle,
  Repeat,
  Repeat1,
  Volume2,
  VolumeX,
  ListMusic,
  Heart,
} from "lucide-react";
import { usePlayerStore } from "@/store/playerStore";
import { coverUrl, api } from "@/lib/api";
import { formatDuration } from "@/lib/format";
import { seekTo } from "@/lib/audioController";
import { IconButton } from "@/components/ui/IconButton";
import { Slider } from "@/components/ui/Slider";
import { NowPlayingSheet } from "./NowPlayingSheet";

export function BottomPlayer() {
  const currentSong = usePlayerStore((s) => s.currentSong());
  const isPlaying = usePlayerStore((s) => s.isPlaying);
  const currentTime = usePlayerStore((s) => s.currentTime);
  const duration = usePlayerStore((s) => s.duration);
  const volume = usePlayerStore((s) => s.volume);
  const muted = usePlayerStore((s) => s.muted);
  const shuffle = usePlayerStore((s) => s.shuffle);
  const repeat = usePlayerStore((s) => s.repeat);

  const togglePlay = usePlayerStore((s) => s.togglePlay);
  const next = usePlayerStore((s) => s.next);
  const previous = usePlayerStore((s) => s.previous);
  const toggleShuffle = usePlayerStore((s) => s.toggleShuffle);
  const cycleRepeat = usePlayerStore((s) => s.cycleRepeat);
  const setVolume = usePlayerStore((s) => s.setVolume);
  const toggleMute = usePlayerStore((s) => s.toggleMute);
  const setCurrentTime = usePlayerStore((s) => s.setCurrentTime);

  const [sheetOpen, setSheetOpen] = useState(false);
  const [starred, setStarred] = useState(false);

  async function toggleStar() {
    if (!currentSong) return;
    if (starred || currentSong.starred) {
      await api.delete(`/api/songs/${currentSong.id}/star`);
    } else {
      await api.post(`/api/songs/${currentSong.id}/star`);
    }
    setStarred((s) => !s);
  }

  if (!currentSong) {
    return (
      <footer className="flex h-20 flex-shrink-0 items-center justify-center border-t border-border-subtle bg-bg-elevated px-4 text-sm text-fg-muted">
        Nothing playing — pick a song to get started
      </footer>
    );
  }

  const isStarred = starred || currentSong.starred;

  return (
    <>
      <footer className="flex h-20 flex-shrink-0 items-center gap-4 border-t border-border-subtle bg-bg-elevated px-4">
        <button className="flex min-w-0 items-center gap-3 text-left md:w-64" onClick={() => setSheetOpen(true)}>
          <div className="relative h-14 w-14 flex-shrink-0 overflow-hidden rounded-md bg-bg-elevated-2">
            <Image src={coverUrl(currentSong.coverArtId, 120)} alt={currentSong.title} fill sizes="56px" className="object-cover" unoptimized />
          </div>
          <div className="min-w-0 hidden sm:block">
            <p className="truncate text-sm font-medium text-fg-primary">{currentSong.title}</p>
            <p className="truncate text-xs text-fg-secondary">{currentSong.artistName ?? "Unknown Artist"}</p>
          </div>
        </button>

        <IconButton size="sm" className="hidden sm:inline-flex" active={isStarred} onClick={toggleStar} aria-label="Star">
          <Heart size={16} fill={isStarred ? "currentColor" : "none"} />
        </IconButton>

        <div className="flex flex-1 flex-col items-center gap-1">
          <div className="flex items-center gap-3">
            <IconButton size="sm" active={shuffle} onClick={toggleShuffle} aria-label="Shuffle" className="hidden sm:inline-flex">
              <Shuffle size={16} />
            </IconButton>
            <IconButton size="sm" onClick={previous} aria-label="Previous">
              <SkipBack size={18} />
            </IconButton>
            <IconButton size="md" onClick={togglePlay} className="bg-fg-primary text-bg-base hover:bg-fg-primary" aria-label={isPlaying ? "Pause" : "Play"}>
              {isPlaying ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" />}
            </IconButton>
            <IconButton size="sm" onClick={next} aria-label="Next">
              <SkipForward size={18} />
            </IconButton>
            <IconButton
              size="sm"
              active={repeat !== "off"}
              onClick={cycleRepeat}
              aria-label="Repeat"
              className="hidden sm:inline-flex"
            >
              {repeat === "one" ? <Repeat1 size={16} /> : <Repeat size={16} />}
            </IconButton>
          </div>
          <div className="hidden w-full max-w-lg items-center gap-2 sm:flex">
            <span className="w-10 text-right text-xs text-fg-muted">{formatDuration(currentTime)}</span>
            <Slider
              min={0}
              max={duration || 0}
              value={Math.min(currentTime, duration || 0)}
              onChange={(e) => {
                const value = Number(e.target.value);
                setCurrentTime(value);
                seekTo(value);
              }}
              className="flex-1"
              aria-label="Seek"
            />
            <span className="w-10 text-xs text-fg-muted">{formatDuration(duration)}</span>
          </div>
        </div>

        <div className="hidden items-center gap-2 md:flex md:w-40">
          <Link href="/queue" aria-label="Queue">
            <IconButton size="sm">
              <ListMusic size={16} />
            </IconButton>
          </Link>
          <IconButton size="sm" onClick={toggleMute} aria-label="Mute">
            {muted || volume === 0 ? <VolumeX size={16} /> : <Volume2 size={16} />}
          </IconButton>
          <Slider
            min={0}
            max={1}
            step={0.01}
            value={muted ? 0 : volume}
            onChange={(e) => setVolume(Number(e.target.value))}
            className="w-20"
            aria-label="Volume"
          />
        </div>
      </footer>

      <NowPlayingSheet open={sheetOpen} onClose={() => setSheetOpen(false)} />
    </>
  );
}
