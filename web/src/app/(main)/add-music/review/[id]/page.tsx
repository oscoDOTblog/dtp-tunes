"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import type { IngestJob } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export default function ReviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { user } = useAuth();
  const router = useRouter();
  const [job, setJob] = useState<IngestJob | null>(null);
  const [tracks, setTracks] = useState<{ id: number; title: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user?.role !== "admin") return;
    let stopped = false;
    const load = async () => {
      try {
        const data = await api.get<IngestJob>(`/api/admin/ingest/jobs/${id}`);
        if (!stopped) {
          setJob(data);
          setTracks((current) => current.length ? current : data.tracks);
        }
      } catch (err) { if (!stopped) setError(err instanceof ApiError ? err.message : "Could not load job"); }
    };
    void load();
    const timer = window.setInterval(load, 2000);
    return () => { stopped = true; window.clearInterval(timer); };
  }, [id, user?.role]);

  function move(index: number, direction: number) {
    const next = [...tracks];
    const target = index + direction;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    setTracks(next);
  }

  async function save() {
    setBusy(true); setError(null);
    try {
      await api.post(`/api/admin/ingest/jobs/${id}/save`, { tracks });
      router.push("/add-music/queue");
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not save tracks"); }
    finally { setBusy(false); }
  }

  if (user?.role !== "admin") return <p className="p-6 text-fg-secondary">Admin access required.</p>;
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-5 p-6 pb-32">
      <div><h1 className="text-3xl font-bold text-fg-primary">Review tracks</h1><p className="text-sm text-fg-secondary">{job?.album.title || "Loading…"} · {job?.status || "waiting"}</p></div>
      {job?.status === "downloading" && <p className="text-sm text-fg-secondary">Downloading… {job.currentTitle || ""}</p>}
      {job?.status === "failed" && <p className="text-sm text-danger">{job.error}</p>}
      {tracks.map((track, index) => <div key={track.id} className="flex items-center gap-2">
        <span className="w-8 text-sm text-fg-secondary">{index + 1}</span>
        <Input value={track.title} onChange={(event) => setTracks(tracks.map((item) => item.id === track.id ? { ...item, title: event.target.value } : item))} className="flex-1" />
        <Button variant="secondary" size="sm" onClick={() => move(index, -1)} disabled={index === 0}>↑</Button>
        <Button variant="secondary" size="sm" onClick={() => move(index, 1)} disabled={index === tracks.length - 1}>↓</Button>
      </div>)}
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      <div className="flex gap-3"><Button onClick={save} disabled={busy || job?.status !== "readyForReview" || tracks.length === 0 || tracks.some((track) => !track.title.trim())}>{busy ? "Saving…" : "Save to library"}</Button><Link href="/add-music/queue" className="self-center text-sm text-accent">Back to queue</Link></div>
    </div>
  );
}
