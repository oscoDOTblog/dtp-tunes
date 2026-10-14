"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { uploadFormWithProgress, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export default function UploadMusicPage() {
  const { user } = useAuth();
  const [cover, setCover] = useState<File | null>(null);
  const [artist, setArtist] = useState("");
  const [album, setAlbum] = useState("");
  const [year, setYear] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [coverPreview, setCoverPreview] = useState<string | null>(null);
  const [tracks, setTracks] = useState<{ id: string; file: File; title: string }[]>([]);
  const [uploadProgress, setUploadProgress] = useState<{ loaded: number; total: number } | null>(null);

  useEffect(() => {
    if (!cover) { setCoverPreview(null); return; }
    const url = URL.createObjectURL(cover);
    setCoverPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [cover]);

  if (user?.role !== "admin") return <p className="p-6 text-fg-secondary">Admin access required.</p>;
  async function submit() {
    setBusy(true); setError(null); setResult(null); setUploadProgress({ loaded: 0, total: 0 });
    const body = new FormData();
    for (const track of tracks) body.append("files", track.file);
    if (cover) body.append("cover", cover);
    body.append("artist", artist); body.append("album", album); body.append("year", year);
    body.append("track_titles", JSON.stringify(tracks.map((track) => track.title)));
    try {
      const response = await uploadFormWithProgress<{ count: number; artist: string; album: string; scanError?: string | null }>(
        "/api/admin/ingest/upload",
        body,
        (loaded, total) => setUploadProgress({ loaded, total }),
      );
      setResult(`Saved ${response.count} tracks to ${response.artist} / ${response.album}${response.scanError ? `. Scan failed: ${response.scanError}` : ". Library scan queued."}`);
      setTracks([]); setCover(null);
    } catch (err) { setError(err instanceof ApiError ? err.message : "Upload failed"); }
    finally { setBusy(false); setUploadProgress(null); }
  }

  function selectFiles(selected: File[]) {
    setTracks(selected.map((file, index) => ({
      id: `${file.name}-${file.size}-${file.lastModified}-${index}`,
      file,
      title: file.name.replace(/\.[^.]+$/, "").replace(/^\s*\d+[\s._-]+/, "").trim(),
    })));
    setError(null); setResult(null);
  }

  function moveTrack(index: number, direction: number) {
    const target = index + direction;
    if (target < 0 || target >= tracks.length) return;
    const next = [...tracks];
    [next[index], next[target]] = [next[target], next[index]];
    setTracks(next);
  }

  function removeTrack(id: string) {
    const next = tracks.filter((track) => track.id !== id);
    setTracks(next);
  }

  function formatSize(bytes: number) {
    return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  return <div className="mx-auto flex max-w-3xl flex-col gap-5 p-6 pb-32">
    <div><h1 className="text-3xl font-bold text-fg-primary">Upload audio</h1><p className="text-sm text-fg-secondary">Choose files, then review the album and track list before anything is uploaded.</p></div>
    <label className="rounded-xl border border-dashed border-border-subtle bg-bg-elevated p-6 text-sm text-fg-secondary">Choose MP3, FLAC, M4A, Ogg, Opus, or WAV files
      <input type="file" multiple accept=".mp3,.flac,.m4a,.ogg,.opus,.wav,audio/mpeg,audio/flac,audio/mp4,audio/ogg,audio/opus,audio/wav" onChange={(event) => selectFiles(Array.from(event.target.files ?? []))} className="mt-3 block w-full" />
    </label>
    {tracks.length > 0 && <section className="flex flex-col gap-5 rounded-xl border border-border-subtle bg-bg-elevated p-5">
      <h2 className="text-lg font-semibold text-fg-primary">Review album details</h2>
      <div className="grid gap-5 sm:grid-cols-[10rem_1fr]">
        <div className="flex flex-col gap-2">
          <div className="aspect-square overflow-hidden rounded-lg border border-border-subtle bg-bg-primary">
            {coverPreview ? <img src={coverPreview} alt="Album cover preview" className="h-full w-full object-cover" /> : <div className="flex h-full items-center justify-center px-4 text-center text-xs text-fg-secondary">No album cover selected</div>}
          </div>
          <label className="cursor-pointer text-center text-sm text-accent hover:underline">{cover ? "Change cover" : "Choose cover"}
            <input type="file" accept="image/jpeg,image/png,image/webp,image/gif,image/avif" onChange={(event) => setCover(event.target.files?.[0] ?? null)} className="sr-only" />
          </label>
        </div>
        <div className="flex flex-col gap-3">
          <label className="text-sm text-fg-secondary">Album title<Input value={album} onChange={(event) => setAlbum(event.target.value)} className="mt-1 w-full" placeholder="Unknown Album" /></label>
          <label className="text-sm text-fg-secondary">Artist<Input value={artist} onChange={(event) => setArtist(event.target.value)} className="mt-1 w-full" placeholder="Unknown Artist" /></label>
          <label className="text-sm text-fg-secondary">Year<Input value={year} onChange={(event) => setYear(event.target.value)} className="mt-1 w-full" placeholder="Optional" /></label>
          <p className="text-xs text-fg-secondary">{tracks.length} {tracks.length === 1 ? "track" : "tracks"} · {formatSize(tracks.reduce((total, track) => total + track.file.size, 0))}</p>
        </div>
      </div>
      <div className="flex flex-col gap-2">
        <h3 className="text-sm font-semibold text-fg-primary">Track order and names</h3>
        {tracks.map((track, index) => <div key={track.id} className="flex items-center gap-2 rounded-lg border border-border-subtle bg-bg-primary p-2">
          <span className="w-7 text-center text-sm font-medium text-fg-secondary">{index + 1}</span>
          <div className="min-w-0 flex-1">
            <Input aria-label={`Track ${index + 1} title`} value={track.title} onChange={(event) => setTracks(tracks.map((item) => item.id === track.id ? { ...item, title: event.target.value } : item))} className="w-full" />
            <p className="mt-1 truncate px-1 text-xs text-fg-secondary">{track.file.name} · {formatSize(track.file.size)}</p>
          </div>
          <div className="flex gap-1">
            <Button aria-label={`Move ${track.title} up`} variant="secondary" size="sm" onClick={() => moveTrack(index, -1)} disabled={index === 0}>↑</Button>
            <Button aria-label={`Move ${track.title} down`} variant="secondary" size="sm" onClick={() => moveTrack(index, 1)} disabled={index === tracks.length - 1}>↓</Button>
            <Button aria-label={`Remove ${track.title}`} variant="ghost" size="sm" onClick={() => removeTrack(track.id)}>Remove</Button>
          </div>
        </div>)}
      </div>
    </section>}
    {error && <p role="alert" className="text-sm text-danger">{error}</p>}
    {result && <p role="status" className="text-sm text-accent">{result}</p>}
    {busy && uploadProgress && <div className="flex flex-col gap-2" aria-live="polite">
      <div className="flex justify-between text-sm text-fg-secondary">
        <span>{uploadProgress.total > 0 && uploadProgress.loaded >= uploadProgress.total ? "Processing files…" : "Uploading files…"}</span>
        <span>{uploadProgress.total > 0 ? `${Math.round((uploadProgress.loaded / uploadProgress.total) * 100)}%` : "Starting…"}</span>
      </div>
      <div
        role="progressbar"
        aria-label="File upload progress"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={uploadProgress.total > 0 ? Math.round((uploadProgress.loaded / uploadProgress.total) * 100) : 0}
        className="h-2 overflow-hidden rounded-full bg-bg-elevated"
      >
        <div className="h-full rounded-full bg-accent transition-[width] duration-200" style={{ width: uploadProgress.total > 0 ? `${(uploadProgress.loaded / uploadProgress.total) * 100}%` : "0%" }} />
      </div>
      {uploadProgress.total > 0 && <p className="text-xs text-fg-secondary">{formatSize(uploadProgress.loaded)} of {formatSize(uploadProgress.total)}</p>}
    </div>}
    <div className="flex gap-3"><Button onClick={submit} disabled={busy || tracks.length === 0 || tracks.some((track) => !track.title.trim())}>{busy ? "Uploading…" : "Upload to library"}</Button><Link href="/add-music" className="self-center text-sm text-accent">Back</Link></div>
  </div>;
}
