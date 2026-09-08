"use client";

import { useState } from "react";
import Image from "next/image";
import { Pause, Play, Heart, MoreVertical, ListPlus, Download } from "lucide-react";
import type { Song } from "@/lib/types";
import { coverUrl, downloadFile, songDownloadUrl } from "@/lib/api";
import { formatDuration } from "@/lib/format";
import { usePlayerStore } from "@/store/playerStore";
import { cn } from "@/lib/utils";
import { ContextMenu, Menu, MenuItem, type ContextMenuPosition } from "@/components/ui/Menu";
import { SaveToPlaylistDialog } from "@/components/music/SaveToPlaylistDialog";
import { useToast } from "@/components/ui/ToastProvider";

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
  const [saveOpen, setSaveOpen] = useState(false);
  const [contextPos, setContextPos] = useState<ContextMenuPosition | null>(null);
  const [downloading, setDownloading] = useState(false);
  const toast = useToast();

  const isCurrent = currentSong?.id === song.id;

  function handlePlay() {
    if (isCurrent) {
      togglePlay();
    } else {
      playQueue(queue, index);
    }
  }

  async function handleDownload() {
    if (downloading) return;
    setDownloading(true);
    try {
      const ext = song.suffix ? `.${song.suffix.toLowerCase()}` : "";
      await downloadFile(songDownloadUrl(song.id), `${song.title}${ext}`);
    } catch {
      toast.error("Failed to download song");
    } finally {
      setDownloading(false);
    }
  }

  const menuItems = (
    <>
      <MenuItem onClick={() => setSaveOpen(true)}>
        <ListPlus size={16} />
        Save to playlist
      </MenuItem>
      <MenuItem onClick={handleDownload} disabled={downloading}>
        <Download size={16} />
        {downloading ? "Downloading…" : "Download"}
      </MenuItem>
    </>
  );

  return (
    <>
      <div
        onContextMenu={(event) => {
          event.preventDefault();
          setContextPos({ x: event.clientX, y: event.clientY });
        }}
        className={cn(
          "group grid grid-cols-[2rem_1fr_auto] sm:grid-cols-[2rem_1fr_10rem_3rem_3rem] items-center gap-4 rounded-lg px-3 py-2 hover:bg-bg-hover",
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

        <div className="relative flex h-8 w-10 items-center justify-end text-xs text-fg-secondary">
          <span className="pointer-events-none hidden tabular-nums sm:inline group-hover:sm:hidden">
            {formatDuration(song.duration)}
          </span>
          <div className="flex sm:absolute sm:inset-y-0 sm:right-0 sm:hidden sm:items-center group-hover:sm:flex">
            <Menu
              trigger={
                <button
                  type="button"
                  className="flex h-8 w-8 items-center justify-center rounded-full text-fg-secondary hover:bg-bg-elevated-2 hover:text-fg-primary"
                  aria-label="More options"
                >
                  <MoreVertical size={16} />
                </button>
              }
            >
              {menuItems}
            </Menu>
          </div>
        </div>
      </div>

      <ContextMenu position={contextPos} onClose={() => setContextPos(null)}>
        {menuItems}
      </ContextMenu>

      <SaveToPlaylistDialog song={song} open={saveOpen} onClose={() => setSaveOpen(false)} />
    </>
  );
}
