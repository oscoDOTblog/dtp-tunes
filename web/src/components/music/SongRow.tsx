"use client";

import { useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { Pause, Play, Heart, MoreVertical, ListPlus, Download, FileText, Disc3, Trash2, ListEnd, PlaySquare } from "lucide-react";
import type { Song } from "@/lib/types";
import { api, coverUrl, downloadFile, songDownloadUrl } from "@/lib/api";
import { formatDuration } from "@/lib/format";
import { usePlayerStore } from "@/store/playerStore";
import { cn } from "@/lib/utils";
import { ContextMenu, Menu, MenuItem, type ContextMenuPosition } from "@/components/ui/Menu";
import { SaveToPlaylistDialog } from "@/components/music/SaveToPlaylistDialog";
import { useToast } from "@/components/ui/ToastProvider";
import { LyricsDialog } from "@/components/music/LyricsDialog";

interface SongRowProps {
  song: Song;
  index: number;
  queue: Song[];
  showAlbum?: boolean;
  showCover?: boolean;
  showDetails?: boolean;
  onToggleStar?: (song: Song) => void;
  onDeleted?: () => void;
}

export const detailedSongColumns = "md:grid-cols-[2rem_minmax(0,2fr)_minmax(0,1.4fr)_minmax(0,1.2fr)_3rem_2rem_4rem]";

export function SongRow({ song, index, queue, showAlbum = true, showCover = false, showDetails = false, onToggleStar, onDeleted }: SongRowProps) {
  const router = useRouter();
  const currentSong = usePlayerStore((s) => s.currentSong());
  const isPlaying = usePlayerStore((s) => s.isPlaying);
  const playQueue = usePlayerStore((s) => s.playQueue);
  const playNext = usePlayerStore((s) => s.playNext);
  const addToQueue = usePlayerStore((s) => s.addToQueue);
  const togglePlay = usePlayerStore((s) => s.togglePlay);
  const [saveOpen, setSaveOpen] = useState(false);
  const [lyricsOpen, setLyricsOpen] = useState(false);
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

  async function handleDelete() {
    if (!window.confirm(`Permanently delete “${song.title}”?\n\nThis removes the audio file and cannot be undone.`)) return;
    try {
      await api.delete(`/api/songs/${song.id}`);
      toast.success(`Deleted “${song.title}”`);
      if (onDeleted) onDeleted();
      else window.location.reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete song");
    }
  }

  const menuItems = (
    <>
      <MenuItem onClick={() => {
        playNext(song);
        toast.success(`Playing “${song.title}” next`);
      }}>
        <PlaySquare size={16} />
        Play next
      </MenuItem>
      <MenuItem onClick={() => {
        addToQueue(song);
        toast.success(`Added “${song.title}” to queue`);
      }}>
        <ListEnd size={16} />
        Add to queue
      </MenuItem>
      {song.albumId && (
        <MenuItem onClick={() => router.push(`/album/${encodeURIComponent(song.albumId!)}`)}>
          <Disc3 size={16} />
          View album
        </MenuItem>
      )}
      <MenuItem onClick={() => setSaveOpen(true)}>
        <ListPlus size={16} />
        Save to playlist
      </MenuItem>
      {showDetails && onToggleStar && (
        <MenuItem onClick={() => onToggleStar(song)}>
          <Heart size={16} />
          {song.starred ? "Unlike song" : "Like song"}
        </MenuItem>
      )}
      <MenuItem onClick={handleDownload} disabled={downloading}>
        <Download size={16} />
        {downloading ? "Downloading…" : "Download"}
      </MenuItem>
      {song.canEditLyrics && (
        <>
          <MenuItem onClick={() => setLyricsOpen(true)}>
            <FileText size={16} />
            Edit lyrics
          </MenuItem>
          <MenuItem onClick={handleDelete}>
            <Trash2 size={16} />
            Permanently Delete
          </MenuItem>
        </>
      )}
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
          "group grid grid-cols-[2rem_minmax(0,1fr)_auto] items-center gap-4 rounded-lg px-3 py-2 hover:bg-bg-hover",
          showDetails ? detailedSongColumns : "sm:grid-cols-[2rem_1fr_10rem_3rem_3rem]",
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
            <p className={cn("truncate text-xs text-fg-secondary", showDetails && "md:hidden")}>
              {song.artistName ?? "Unknown Artist"}
              {showDetails && song.albumName && ` · ${song.albumName}`}
              {showDetails && song.year && ` · ${song.year}`}
            </p>
          </div>
        </div>

        {showDetails ? (
          <>
            <p className="hidden truncate text-sm text-fg-secondary md:block" title={song.albumName ?? undefined}>{song.albumName ?? "—"}</p>
            <p className="hidden truncate text-sm text-fg-secondary md:block" title={song.artistName ?? undefined}>{song.artistName ?? "—"}</p>
            <p className="hidden text-sm tabular-nums text-fg-secondary md:block">{song.year ?? "—"}</p>
          </>
        ) : showAlbum ? (
          <p className="hidden truncate text-sm text-fg-secondary sm:block">{song.albumName ?? ""}</p>
        ) : (
          <span className="hidden sm:block" />
        )}

        <button
          onClick={() => onToggleStar?.(song)}
          className={cn(
            "hidden items-center justify-center text-fg-secondary hover:text-accent",
            showDetails ? "md:flex" : "sm:flex",
            song.starred && "text-accent",
            !song.starred && "opacity-0 group-hover:opacity-100"
          )}
          aria-label={song.starred ? "Unstar" : "Star"}
        >
          <Heart size={16} fill={song.starred ? "currentColor" : "none"} />
        </button>

        <div className={cn("relative flex h-8 items-center justify-end text-xs text-fg-secondary", showDetails ? "w-10 md:w-full" : "w-10")}>
          <span className={cn("pointer-events-none hidden tabular-nums", showDetails ? "md:inline" : "sm:inline group-hover:sm:hidden")}>
            {formatDuration(song.duration)}
          </span>
          <div className={cn("flex shrink-0", !showDetails && "sm:absolute sm:inset-y-0 sm:right-0 sm:hidden sm:items-center group-hover:sm:flex")}>
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
      {lyricsOpen && <LyricsDialog song={song} onClose={() => setLyricsOpen(false)} />}
    </>
  );
}
