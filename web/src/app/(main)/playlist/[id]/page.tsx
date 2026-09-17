"use client";

import {
  use,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
} from "react";
import { Play, Pencil, Trash2, Loader2, GripVertical } from "lucide-react";
import { useRouter } from "next/navigation";
import { useFetch } from "@/lib/useFetch";
import { SongRow } from "@/components/music/SongRow";
import { PlaylistCover } from "@/components/music/PlaylistCover";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/components/ui/ToastProvider";
import { api, ApiError } from "@/lib/api";
import { formatAlbumDuration } from "@/lib/format";
import { usePlayerStore } from "@/store/playerStore";
import { usePlaylistsRefresh } from "@/store/playlistsRefreshStore";
import type { Playlist, Song } from "@/lib/types";

interface PlaylistDetail {
  playlist: Playlist;
  songs: Song[];
}

interface PlaylistSongEntry {
  key: string;
  song: Song;
}

interface RowSlot {
  key: string;
  top: number;
  height: number;
}

function insertionIndex(slots: RowSlot[], pointerY: number): number {
  for (let index = 0; index < slots.length; index += 1) {
    if (pointerY < slots[index].top + slots[index].height / 2) return index;
  }
  return slots.length;
}

function moveEntry(entries: PlaylistSongEntry[], from: number, to: number): PlaylistSongEntry[] {
  if (from === to || from < 0 || from >= entries.length || to < 0 || to >= entries.length) return entries;
  const next = [...entries];
  const [entry] = next.splice(from, 1);
  next.splice(to, 0, entry);
  return next;
}

function PlaylistSongs({
  playlistId,
  songs,
  onOrderSaved,
  onSongsChanged,
}: {
  playlistId: string;
  songs: Song[];
  onOrderSaved: (songs: Song[]) => void;
  onSongsChanged: () => void;
}) {
  const toast = useToast();
  const [entries, setEntries] = useState<PlaylistSongEntry[]>(() =>
    songs.map((song, index) => ({ key: `${song.id}-${index}`, song })),
  );
  const [removingIndex, setRemovingIndex] = useState<number | null>(null);
  const [reordering, setReordering] = useState(false);
  const [dragKey, setDragKey] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const entriesRef = useRef(entries);
  useEffect(() => { entriesRef.current = entries; }, [entries]);
  const dragSnapshot = useRef<PlaylistSongEntry[] | null>(null);
  const dragGeometry = useRef<{ heights: Map<string, number>; gap: number; paddingTop: number } | null>(null);
  const lastDragY = useRef(0);
  const listRef = useRef<HTMLDivElement | null>(null);
  const prevTops = useRef(new Map<string, number>());

  useLayoutEffect(() => {
    const rows = listRef.current?.querySelectorAll<HTMLElement>("[data-playlist-entry]");
    const next = new Map<string, number>();
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    rows?.forEach((row) => {
      const key = row.dataset.playlistEntry;
      if (!key) return;
      const top = row.getBoundingClientRect().top;
      const previousTop = prevTops.current.get(key);
      next.set(key, top);
      if (!reduceMotion && previousTop !== undefined && previousTop !== top) {
        row.getAnimations().forEach((animation) => animation.cancel());
        row.animate(
          [{ transform: `translateY(${previousTop - top}px)` }, { transform: "translateY(0)" }],
          { duration: 220, easing: "cubic-bezier(0.2, 0, 0, 1)" },
        );
      }
    });
    prevTops.current = next;
  });

  const mutating = reordering || removingIndex !== null;

  function updateEntries(next: PlaylistSongEntry[]) {
    entriesRef.current = next;
    setEntries(next);
  }

  async function persistOrder(next: PlaylistSongEntry[], rollback: PlaylistSongEntry[]) {
    setReordering(true);
    try {
      await api.patch(`/api/playlists/${playlistId}`, { orderedSongIds: next.map((entry) => entry.song.id) });
      setAnnouncement("New playlist order saved.");
      toast.success("Playlist order saved");
      onOrderSaved(next.map((entry) => entry.song));
    } catch (err) {
      updateEntries(rollback);
      toast.error(err instanceof ApiError ? err.message : "Failed to save playlist order");
    } finally {
      setReordering(false);
    }
  }

  function startDrag(event: PointerEvent<HTMLButtonElement>, entry: PlaylistSongEntry) {
    if (!event.isPrimary || mutating) return;
    if (event.pointerType === "mouse" && event.button !== 0) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    dragSnapshot.current = [...entriesRef.current];
    lastDragY.current = event.clientY;
    const list = listRef.current;
    if (list) {
      const rows = list.querySelectorAll<HTMLElement>("[data-playlist-entry]");
      rows.forEach((row) => row.getAnimations().forEach((animation) => animation.cancel()));
      const heights = new Map<string, number>();
      rows.forEach((row) => {
        const key = row.dataset.playlistEntry;
        if (key) heights.set(key, row.offsetHeight);
      });
      const first = rows[0]?.getBoundingClientRect();
      dragGeometry.current = {
        heights,
        gap: Number.parseFloat(getComputedStyle(list).rowGap) || 0,
        paddingTop: first ? first.top - list.getBoundingClientRect().top : 0,
      };
    }
    setDragKey(entry.key);
  }

  function moveDrag(event: PointerEvent<HTMLButtonElement>, entry: PlaylistSongEntry) {
    const snapshot = dragSnapshot.current;
    const geometry = dragGeometry.current;
    const list = listRef.current;
    if (!snapshot || !geometry || !list || Math.abs(event.clientY - lastDragY.current) < 2) return;
    lastDragY.current = event.clientY;
    const order = entriesRef.current.filter((candidate) => candidate.key !== entry.key);
    const slots: RowSlot[] = [];
    let cursor = list.getBoundingClientRect().top + geometry.paddingTop;
    for (const candidate of order) {
      const height = geometry.heights.get(candidate.key);
      if (height === undefined) return;
      slots.push({ key: candidate.key, top: cursor, height });
      cursor += height + geometry.gap;
    }
    const index = insertionIndex(slots, event.clientY);
    const current = entriesRef.current;
    const without = current.filter((candidate) => candidate.key !== entry.key);
    const clamped = Math.max(0, Math.min(index, without.length));
    updateEntries([...without.slice(0, clamped), entry, ...without.slice(clamped)]);
  }

  function endDrag(commit: boolean) {
    const snapshot = dragSnapshot.current;
    dragSnapshot.current = null;
    dragGeometry.current = null;
    setDragKey(null);
    if (!snapshot) return;
    if (!commit) {
      updateEntries(snapshot);
      return;
    }
    const next = entriesRef.current;
    if (next.every((entry, index) => entry.key === snapshot[index]?.key)) return;
    void persistOrder(next, snapshot);
  }

  async function moveWithKeyboard(entry: PlaylistSongEntry, direction: -1 | 1) {
    if (mutating) return;
    const rollback = entriesRef.current;
    const from = rollback.findIndex((candidate) => candidate.key === entry.key);
    const to = from + direction;
    const next = moveEntry(rollback, from, to);
    if (next === rollback) return;
    updateEntries(next);
    setAnnouncement(`Moved ${entry.song.title} ${direction === -1 ? "up" : "down"}.`);
    await persistOrder(next, rollback);
  }

  function onGripKeyDown(event: KeyboardEvent<HTMLButtonElement>, entry: PlaylistSongEntry) {
    if (event.key === "ArrowUp") { event.preventDefault(); void moveWithKeyboard(entry, -1); }
    else if (event.key === "ArrowDown") { event.preventDefault(); void moveWithKeyboard(entry, 1); }
  }

  async function removeSong(index: number) {
    setRemovingIndex(index);
    try {
      await api.patch(`/api/playlists/${playlistId}`, { songIndexesToRemove: [index] });
      toast.success("Removed from playlist");
      onSongsChanged();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to remove song");
    } finally {
      setRemovingIndex(null);
    }
  }

  const orderedSongs = entries.map((entry) => entry.song);

  return (
    <div className="flex flex-col" ref={listRef}>
      <p role="status" className="sr-only">{announcement}</p>
      {entries.map((entry, index) => (
        <div
          key={entry.key}
          data-playlist-entry={entry.key}
          className={`group flex items-center rounded-lg ${dragKey === entry.key ? "bg-accent-soft" : ""}`}
          onDragStart={(event) => event.preventDefault()}
        >
          <button
            type="button"
            className="ml-1 flex h-8 w-7 shrink-0 touch-none cursor-grab items-center justify-center rounded text-fg-muted hover:bg-bg-hover hover:text-fg-primary focus-visible:outline-2 focus-visible:outline-accent active:cursor-grabbing disabled:cursor-default disabled:opacity-40"
            aria-label={`Reorder ${entry.song.title}. Drag, or use the arrow keys.`}
            disabled={mutating}
            onPointerDown={(event) => startDrag(event, entry)}
            onPointerMove={(event) => moveDrag(event, entry)}
            onPointerUp={() => endDrag(true)}
            onPointerCancel={() => endDrag(false)}
            onKeyDown={(event) => onGripKeyDown(event, entry)}
          >
            <GripVertical size={16} aria-hidden="true" />
          </button>
          <div className="min-w-0 flex-1">
            <SongRow song={entry.song} index={index} queue={orderedSongs} showAlbum showCover />
          </div>
          <button
            type="button"
            onClick={() => removeSong(index)}
            disabled={mutating}
            className={
              removingIndex === index
                ? "mr-2 block text-fg-muted"
                : "mr-2 hidden text-fg-muted hover:text-danger disabled:pointer-events-none disabled:opacity-40 group-hover:block group-focus-within:block"
            }
            aria-label={`Remove ${entry.song.title} from playlist`}
          >
            {removingIndex === index ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
          </button>
        </div>
      ))}
    </div>
  );
}

export default function PlaylistPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const toast = useToast();
  const { data, isLoading, error, refetch } = useFetch<PlaylistDetail>(`/api/playlists/${id}`, [id]);
  const playQueue = usePlayerStore((s) => s.playQueue);
  const bumpPlaylists = usePlaylistsRefresh((s) => s.bump);
  const playbackSongsRef = useRef<Song[] | null>(null);
  useEffect(() => { playbackSongsRef.current = data?.songs ?? null; }, [data]);
  const [renaming, setRenaming] = useState(false);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const mutating = saving || deleting;

  async function saveName() {
    setSaving(true);
    try {
      await api.patch(`/api/playlists/${id}`, { name });
      setRenaming(false);
      refetch();
      bumpPlaylists();
      toast.success("Playlist renamed");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to rename playlist");
    } finally {
      setSaving(false);
    }
  }

  async function deletePlaylist() {
    setDeleting(true);
    try {
      await api.delete(`/api/playlists/${id}`);
      bumpPlaylists();
      toast.success("Playlist deleted");
      router.push("/library");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to delete playlist");
      setDeleting(false);
    }
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <Skeleton className="h-40 w-full rounded-2xl" />
      </div>
    );
  }
  if (error || !data) return <ErrorState message={error ?? "Playlist not found"} onRetry={refetch} />;

  const { playlist, songs } = data;

  return (
    <div className="flex flex-col gap-8 p-6 pb-32">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
        <PlaylistCover coverArtIds={playlist.coverArtIds} size="lg" alt={playlist.name} />
        <div className="flex min-w-0 flex-1 flex-col gap-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-fg-secondary">Playlist</p>
          {renaming ? (
            <div className="flex max-w-md items-center gap-2">
              <Input value={name} onChange={(e) => setName(e.target.value)} autoFocus disabled={saving} />
              <Button size="sm" onClick={saveName} disabled={saving || !name.trim()}>
                {saving && <Loader2 size={14} className="animate-spin" />}
                {saving ? "Saving…" : "Save"}
              </Button>
            </div>
          ) : (
            <h1 className="text-3xl font-bold text-fg-primary sm:text-4xl">{playlist.name}</h1>
          )}
          <p className="text-sm text-fg-secondary">
            {playlist.songCount} songs · {formatAlbumDuration(playlist.duration)}
          </p>
          <div className="flex items-center gap-2">
            <Button onClick={() => playQueue(playbackSongsRef.current ?? songs, 0)} disabled={songs.length === 0}>
              <Play size={16} fill="currentColor" /> Play
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={mutating}
              onClick={() => {
                setName(playlist.name);
                setRenaming(true);
              }}
            >
              <Pencil size={14} /> Rename
            </Button>
            <Button variant="secondary" size="sm" onClick={deletePlaylist} disabled={mutating}>
              {deleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
              {deleting ? "Deleting…" : "Delete"}
            </Button>
          </div>
        </div>
      </div>

      {songs.length === 0 ? (
        <EmptyState title="This playlist is empty" description="Add songs from any album or search result." />
      ) : (
        <PlaylistSongs
          key={playlist.updatedAt}
          playlistId={id}
          songs={songs}
          onOrderSaved={(orderedSongs) => { playbackSongsRef.current = orderedSongs; bumpPlaylists(); }}
          onSongsChanged={() => { refetch(); bumpPlaylists(); }}
        />
      )}
    </div>
  );
}
