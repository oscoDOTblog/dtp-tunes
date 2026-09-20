"use client";

import { useState } from "react";
import Link from "next/link";
import { uploadForm, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export default function UploadMusicPage() {
  const { user } = useAuth();
  const [files, setFiles] = useState<File[]>([]);
  const [cover, setCover] = useState<File | null>(null);
  const [artist, setArtist] = useState("");
  const [album, setAlbum] = useState("");
  const [year, setYear] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  if (user?.role !== "admin") return <p className="p-6 text-fg-secondary">Admin access required.</p>;
  async function submit() {
    setBusy(true); setError(null); setResult(null);
    const body = new FormData();
    for (const file of files) body.append("files", file);
    if (cover) body.append("cover", cover);
    body.append("artist", artist); body.append("album", album); body.append("year", year);
    try {
      const response = await uploadForm<{ count: number; artist: string; album: string; scanError?: string | null }>("/api/admin/ingest/upload", body);
      setResult(`Saved ${response.count} tracks to ${response.artist} / ${response.album}${response.scanError ? `. Scan failed: ${response.scanError}` : ". Library scan queued."}`);
      setFiles([]);
    } catch (err) { setError(err instanceof ApiError ? err.message : "Upload failed"); }
    finally { setBusy(false); }
  }
  return <div className="mx-auto flex max-w-3xl flex-col gap-5 p-6 pb-32">
    <div><h1 className="text-3xl font-bold text-fg-primary">Upload MP3s</h1><p className="text-sm text-fg-secondary">Files are merged into the shared music library.</p></div>
    <label className="rounded-xl border border-dashed border-border-subtle bg-bg-elevated p-6 text-sm text-fg-secondary">Choose MP3 files
      <input type="file" multiple accept=".mp3,audio/mpeg" onChange={(event) => setFiles(Array.from(event.target.files ?? []))} className="mt-3 block w-full" />
    </label>
    {files.length > 0 && <p className="text-sm text-fg-secondary">{files.length} files selected</p>}
    <label className="text-sm text-fg-secondary">Artist (optional)<Input value={artist} onChange={(event) => setArtist(event.target.value)} className="mt-1 w-full" /></label>
    <label className="text-sm text-fg-secondary">Album (optional)<Input value={album} onChange={(event) => setAlbum(event.target.value)} className="mt-1 w-full" /></label>
    <label className="text-sm text-fg-secondary">Year (optional)<Input value={year} onChange={(event) => setYear(event.target.value)} className="mt-1 w-full" /></label>
    <label className="text-sm text-fg-secondary">Cover (optional JPEG/PNG)<input type="file" accept="image/jpeg,image/png" onChange={(event) => setCover(event.target.files?.[0] ?? null)} className="mt-1 block w-full" /></label>
    {error && <p role="alert" className="text-sm text-danger">{error}</p>}
    {result && <p role="status" className="text-sm text-accent">{result}</p>}
    <div className="flex gap-3"><Button onClick={submit} disabled={busy || files.length === 0}>{busy ? "Uploading…" : "Save to library"}</Button><Link href="/add-music" className="self-center text-sm text-accent">Back</Link></div>
  </div>;
}
