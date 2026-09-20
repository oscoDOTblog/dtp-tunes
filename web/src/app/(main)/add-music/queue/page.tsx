"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import type { IngestJob } from "@/lib/types";
import { Button } from "@/components/ui/Button";

export default function IngestQueuePage() {
  const { user } = useAuth();
  const [jobs, setJobs] = useState<IngestJob[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user?.role !== "admin") return;
    let stopped = false;
    const load = async () => {
      try {
        const data = await api.get<{ jobs: IngestJob[] }>("/api/admin/ingest/jobs");
        if (!stopped) { setJobs(data.jobs); setError(null); }
      } catch (err) { if (!stopped) setError(err instanceof ApiError ? err.message : "Could not load jobs"); }
    };
    void load();
    const timer = window.setInterval(load, 2000);
    return () => { stopped = true; window.clearInterval(timer); };
  }, [user?.role]);

  async function action(path: string, method: "post" | "delete") {
    setBusy(true);
    try {
      if (method === "post") await api.post(path);
      else await api.delete(path);
      const data = await api.get<{ jobs: IngestJob[] }>("/api/admin/ingest/jobs");
      setJobs(data.jobs); setError(null);
    } catch (err) { setError(err instanceof ApiError ? err.message : "Action failed"); }
    finally { setBusy(false); }
  }

  if (user?.role !== "admin") return <p className="p-6 text-fg-secondary">Admin access required.</p>;
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-5 p-6 pb-32">
      <div className="flex items-center justify-between"><h1 className="text-3xl font-bold text-fg-primary">Music queue</h1><Link href="/add-music" className="text-sm text-accent">New download</Link></div>
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      <Button variant="secondary" size="sm" className="self-start" disabled={busy || !jobs.some((job) => ["completed", "failed", "cancelled"].includes(job.status))} onClick={() => action("/api/admin/ingest/jobs", "delete")}>Clear finished</Button>
      {jobs.length === 0 && <p className="text-fg-secondary">No download jobs yet.</p>}
      {jobs.map((job) => (
        <article key={job.id} className="rounded-xl border border-border-subtle bg-bg-elevated p-4">
          <div className="flex items-start justify-between gap-3"><div><h2 className="font-semibold text-fg-primary">{job.album.title || job.url}</h2><p className="text-sm text-fg-secondary">{job.album.artist || "Unknown artist"} · {job.mode === "oneOff" ? "Review" : "Background"}</p></div><span className="text-sm text-accent">{job.status}</span></div>
          {job.currentTitle && <p className="mt-2 text-xs text-fg-secondary">Current: {job.currentTitle}</p>}
          {job.total > 0 && <p className="text-xs text-fg-secondary">{job.current} / {job.total} tracks</p>}
          {job.error && <p className="mt-2 text-sm text-danger">{job.error}</p>}
          {job.scanError && <p className="mt-2 text-sm text-danger">Saved, but scan failed: {job.scanError}</p>}
          <div className="mt-3 flex flex-wrap gap-2">
            {job.status === "readyForReview" && <Link href={`/add-music/review/${job.id}`} className="text-sm text-accent">Review tracks</Link>}
            {["queued", "downloading", "readyForReview"].includes(job.status) && <Button variant="secondary" size="sm" disabled={busy} onClick={() => action(`/api/admin/ingest/jobs/${job.id}/cancel`, "post")}>Cancel</Button>}
            {["failed", "cancelled"].includes(job.status) && <Button variant="secondary" size="sm" disabled={busy} onClick={() => action(`/api/admin/ingest/jobs/${job.id}/retry`, "post")}>Retry</Button>}
            {["completed", "failed", "cancelled"].includes(job.status) && <Button variant="ghost" size="sm" disabled={busy} onClick={() => action(`/api/admin/ingest/jobs/${job.id}`, "delete")}>Remove</Button>}
          </div>
        </article>
      ))}
    </div>
  );
}
