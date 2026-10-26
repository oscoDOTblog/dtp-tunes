"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Link2, Upload } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import type { IngestJob } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

interface Metadata { title: string; artist: string; year: string; thumbnailUrl?: string | null }

export default function AddMusicPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [selectedMode, setSelectedMode] = useState<"link" | null>(null);
  const [metadataLoaded, setMetadataLoaded] = useState(false);
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [artist, setArtist] = useState("");
  const [year, setYear] = useState("");
  const [thumbnailUrl, setThumbnailUrl] = useState<string | null>(null);
  const [cover, setCover] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (user?.role !== "admin") return <p className="p-6 text-fg-secondary">Admin access required.</p>;

  async function loadMetadata() {
    setBusy(true); setError(null); setMetadataLoaded(false);
    try {
      const data = await api.post<Metadata>("/api/admin/ingest/metadata", { url });
      setTitle(data.title); setArtist(data.artist); setYear(data.year); setThumbnailUrl(data.thumbnailUrl ?? null);
      setMetadataLoaded(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load metadata");
    } finally { setBusy(false); }
  }

  async function enqueue(mode: "oneOff" | "queue") {
    setBusy(true); setError(null);
    try {
      const job = await api.post<IngestJob>("/api/admin/ingest/jobs", {
        url, mode, album: { title, artist, year }, coverBase64: cover,
      });
      router.push(mode === "oneOff" ? `/add-music/review/${job.id}` : "/add-music/queue");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start download");
    } finally { setBusy(false); }
  }

  async function selectCover(file: File | undefined) {
    if (!file) return;
    if (file.size > 8 * 1024 * 1024) { setError("Cover must be smaller than 8 MiB"); return; }
    const data = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result).split(",")[1] ?? "");
      reader.onerror = () => reject(new Error("Cannot read cover"));
      reader.readAsDataURL(file);
    });
    setCover(data);
  }

  function resetLinkDetails(nextUrl: string) {
    setUrl(nextUrl);
    setMetadataLoaded(false);
    setTitle("");
    setArtist("");
    setYear("");
    setThumbnailUrl(null);
    setCover(null);
    setError(null);
  }

  function backToOptions() {
    resetLinkDetails("");
    setSelectedMode(null);
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 p-6 pb-32">
      <div className="flex items-center justify-between gap-3">
        <div><h1 className="text-3xl font-bold text-fg-primary">Add Music</h1><p className="text-sm text-fg-secondary">Download a track or playlist into your library.</p></div>
        <Link href="/add-music/queue" className="text-sm text-accent hover:underline">View queue</Link>
      </div>
      {!selectedMode && <div className="grid gap-4 sm:grid-cols-2">
        <button
          type="button"
          onClick={() => setSelectedMode("link")}
          className="group flex min-h-52 cursor-pointer flex-col items-start justify-between rounded-2xl border border-border-subtle bg-bg-elevated p-6 text-left transition-colors hover:border-accent hover:bg-bg-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-bg-primary text-accent"><Link2 aria-hidden="true" size={24} /></span>
          <span>
            <span className="block text-xl font-semibold text-fg-primary">Upload with Link</span>
            <span className="mt-2 block text-sm text-fg-secondary">Download music from YouTube, SoundCloud, or another supported URL.</span>
          </span>
        </button>
        <button
          type="button"
          onClick={() => router.push("/add-music/upload")}
          className="group flex min-h-52 cursor-pointer flex-col items-start justify-between rounded-2xl border border-border-subtle bg-bg-elevated p-6 text-left transition-colors hover:border-accent hover:bg-bg-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-bg-primary text-accent"><Upload aria-hidden="true" size={24} /></span>
          <span>
            <span className="block text-xl font-semibold text-fg-primary">Upload with Files</span>
            <span className="mt-2 block text-sm text-fg-secondary">Choose audio files from your device and add them directly to the library.</span>
          </span>
        </button>
      </div>}
      {selectedMode === "link" && <>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input value={url} onChange={(event) => resetLinkDetails(event.target.value)} placeholder="YouTube, SoundCloud, or other supported URL" className="flex-1" />
          <Button variant="secondary" onClick={loadMetadata} disabled={busy || !url.trim()}>{busy ? "Loading…" : "Load details"}</Button>
        </div>
        {error && <p role="alert" className="text-sm text-danger">{error}</p>}
        {metadataLoaded && <section className="flex flex-col gap-4 rounded-xl border border-border-subtle bg-bg-elevated p-5">
        <h2 className="text-lg font-semibold text-fg-primary">Review album details</h2>
        <label className="text-sm text-fg-secondary">Title<Input value={title} onChange={(event) => setTitle(event.target.value)} className="mt-1 w-full" /></label>
        <label className="text-sm text-fg-secondary">Artist<Input value={artist} onChange={(event) => setArtist(event.target.value)} className="mt-1 w-full" /></label>
        <label className="text-sm text-fg-secondary">Year<Input value={year} onChange={(event) => setYear(event.target.value)} className="mt-1 w-full" /></label>
        {thumbnailUrl && <div role="img" aria-label="Source cover preview" className="h-40 w-40 rounded-lg bg-cover bg-center" style={{ backgroundImage: `url(${thumbnailUrl})` }} />}
        <label className="text-sm text-fg-secondary">Custom cover (JPEG, PNG, WebP, GIF, or AVIF)
          <input type="file" accept="image/jpeg,image/png,image/webp,image/gif,image/avif" onChange={(event) => void selectCover(event.target.files?.[0])} className="mt-1 block w-full text-sm" />
        </label>
        {cover && <p className="text-xs text-accent">Custom cover selected</p>}
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => enqueue("oneOff")} disabled={busy || !url.trim()}>{busy ? "Working…" : "Download & review tracks"}</Button>
          <Button variant="secondary" onClick={() => enqueue("queue")} disabled={busy || !url.trim()}>Add to background queue</Button>
        </div>
        </section>}
        <button type="button" onClick={backToOptions} className="w-fit cursor-pointer text-sm text-accent hover:underline">Back to upload options</button>
      </>}
    </div>
  );
}
