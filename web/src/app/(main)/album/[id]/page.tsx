"use client";

import { use, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Download, ListPlus, Play, Trash2 } from "lucide-react";
import { useFetch } from "@/lib/useFetch";
import { SongRow } from "@/components/music/SongRow";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { Button } from "@/components/ui/Button";
import { albumDownloadUrl, coverUrl, downloadFile, api, ApiError } from "@/lib/api";
import { formatAlbumDuration } from "@/lib/format";
import { usePlayerStore } from "@/store/playerStore";
import { useAuth } from "@/lib/useAuth";
import { useToast } from "@/components/ui/ToastProvider";
import { SaveToPlaylistDialog } from "@/components/music/SaveToPlaylistDialog";
import type { Album, Song } from "@/lib/types";

interface AlbumDetail {
  album: Album;
  songs: Song[];
}

export default function AlbumPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { user } = useAuth();
  const toast = useToast();
  const { data, isLoading, error, refetch } = useFetch<AlbumDetail>(`/api/albums/${id}`, [id]);
  const playQueue = usePlayerStore((s) => s.playQueue);
  const [playlistOpen, setPlaylistOpen] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function toggleStar(song: Song) {
    if (song.starred) await api.delete(`/api/songs/${song.id}/star`);
    else await api.post(`/api/songs/${song.id}/star`);
    refetch();
  }

  async function downloadAlbum(name: string) {
    setDownloading(true);
    try {
      await downloadFile(albumDownloadUrl(id), `${name}.zip`);
    } catch {
      toast.error("Failed to download album");
    } finally {
      setDownloading(false);
    }
  }

  async function deleteAlbum(name: string, songCount: number) {
    const confirmed = window.confirm(
      `Permanently delete “${name}” and its ${songCount} ${songCount === 1 ? "song" : "songs"}?\n\nThe audio files will be removed and this cannot be undone.`,
    );
    if (!confirmed) return;
    setDeleting(true);
    try {
      await api.delete(`/api/albums/${id}`);
      toast.success(`Deleted “${name}”`);
      router.push("/library");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to delete album");
      setDeleting(false);
    }
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    );
  }
  if (error || !data) return <ErrorState message={error ?? "Album not found"} onRetry={refetch} />;

  const { album, songs } = data;

  return (
    <div className="grid gap-8 p-5 pb-32 sm:p-6 lg:grid-cols-[minmax(17rem,22rem)_minmax(0,1fr)] lg:items-start lg:gap-10 xl:gap-14">
      <aside className="flex flex-col items-center text-center lg:sticky lg:top-6">
        <div className="mb-4 text-sm font-medium text-fg-primary">
          {album.artistId ? <Link href={`/artist/${album.artistId}`} className="hover:underline">{album.artistName}</Link> : album.artistName ?? "Unknown Artist"}
        </div>
        <div className="relative aspect-square w-full max-w-80 overflow-hidden rounded-2xl bg-bg-elevated-2 shadow-2xl lg:max-w-none">
          <Image src={coverUrl(album.coverArtId, 700)} alt={album.name} fill sizes="(min-width: 1024px) 352px, 320px" className="object-cover" unoptimized />
        </div>
        <h1 className="mt-6 text-3xl font-bold text-fg-primary sm:text-4xl">{album.name}</h1>
        <p className="mt-3 text-sm text-fg-secondary">
          Album{album.year ? ` · ${album.year}` : ""}
        </p>
        <p className="mt-1 text-sm text-fg-secondary">
          {album.songCount} {album.songCount === 1 ? "song" : "songs"} · {formatAlbumDuration(album.duration)}
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <Button onClick={() => playQueue(songs, 0)}><Play size={16} fill="currentColor" /> Play</Button>
          <Button variant="secondary" onClick={() => setPlaylistOpen(true)}><ListPlus size={16} /> Add to playlist</Button>
          <Button variant="secondary" onClick={() => downloadAlbum(album.name)} disabled={downloading}>
            <Download size={16} /> {downloading ? "Downloading…" : "Download"}
          </Button>
          {user?.role === "admin" && <Button variant="outline" className="border-danger text-danger hover:border-danger" onClick={() => deleteAlbum(album.name, songs.length)} disabled={deleting}>
            <Trash2 size={16} /> {deleting ? "Deleting…" : "Permanently Delete"}
          </Button>}
        </div>
      </aside>

      <div className="min-w-0 self-stretch lg:pt-8">
        <div className="flex flex-col gap-1">
          {songs.map((song, index) => (
            <SongRow key={song.id} song={song} index={index} queue={songs} showAlbum={false} onToggleStar={toggleStar} onDeleted={refetch} />
          ))}
        </div>
      </div>
      <SaveToPlaylistDialog songs={songs} open={playlistOpen} onClose={() => setPlaylistOpen(false)} />
    </div>
  );
}
