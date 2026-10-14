"use client";

import { useEffect, useState } from "react";
import { ArrowRightLeft, Check, ExternalLink, Loader2, Search, SkipForward } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import type { ExternalPlaylist, PlaylistTransfer, YouTubeCandidate } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

type IntegrationStatus = { appleMusicConfigured: boolean; youtubeConfigured: boolean; youtubeConnected: boolean; youtubeChannelTitle?: string | null };

function seconds(ms?: number | null) {
  if (!ms) return "—";
  const value = Math.round(ms / 1000);
  return `${Math.floor(value / 60)}:${String(value % 60).padStart(2, "0")}`;
}

export default function ImportPlaylistPage() {
  const { user } = useAuth();
  const [integration, setIntegration] = useState<IntegrationStatus | null>(null);
  const [url, setUrl] = useState("");
  const [job, setJob] = useState<PlaylistTransfer | null>(null);
  const [destinations, setDestinations] = useState<ExternalPlaylist[]>([]);
  const [destinationId, setDestinationId] = useState("");
  const [newName, setNewName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searching, setSearching] = useState<number | null>(null);

  useEffect(() => {
    if (user?.role !== "admin") return;
    let cancelled = false;
    api.get<IntegrationStatus>("/api/playlist-transfers/status").then((value) => {
      if (!cancelled) setIntegration(value);
    });
    return () => { cancelled = true; };
  }, [user?.role]);

  useEffect(() => {
    if (!job || !["queuedExtraction", "extracting", "queuedImport", "importing"].includes(job.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const next = await api.get<PlaylistTransfer>(`/api/playlist-transfers/${job.id}`);
        setJob(next);
        if (next.status === "readyForReview") {
          setNewName(next.source?.name ?? "Imported playlist");
          setDestinations(await api.get<ExternalPlaylist[]>("/api/playlist-transfers/destinations"));
        }
      } catch (err) { setError(err instanceof ApiError ? err.message : "Could not refresh transfer"); }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [job]);

  if (user?.role !== "admin") return <p className="p-6 text-fg-secondary">Admin access required.</p>;

  async function connect() {
    setBusy(true); setError(null);
    try {
      const result = await api.post<{ authorizationUrl: string }>("/api/playlist-transfers/oauth/youtube/start");
      window.location.assign(result.authorizationUrl);
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not start YouTube connection"); setBusy(false); }
  }

  async function disconnect() {
    setBusy(true); setError(null);
    try {
      await api.delete("/api/playlist-transfers/oauth/youtube");
      setIntegration((current) => current ? { ...current, youtubeConnected: false, youtubeChannelTitle: null } : current);
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not disconnect YouTube"); }
    finally { setBusy(false); }
  }

  async function start() {
    setBusy(true); setError(null);
    try { setJob(await api.post<PlaylistTransfer>("/api/playlist-transfers", { sourcePlatform: "appleMusic", sourceUrl: url })); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Could not start transfer"); }
    finally { setBusy(false); }
  }

  async function updateTrack(index: number, videoId?: string, skipped = false) {
    if (!job) return;
    try { setJob(await api.patch<PlaylistTransfer>(`/api/playlist-transfers/${job.id}/tracks/${index}`, { videoId, skipped })); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Could not update match"); }
  }

  async function findAlternatives(index: number) {
    if (!job) return;
    const track = job.tracks[index];
    const query = window.prompt("Search YouTube", `${track.artist} ${track.title}`);
    if (!query) return;
    setSearching(index);
    try {
      const candidates = await api.post<YouTubeCandidate[]>(`/api/playlist-transfers/${job.id}/search?trackIndex=${index}`, { query });
      setJob({ ...job, tracks: job.tracks.map((item, i) => i === index ? { ...item, candidates } : item) });
    } catch (err) { setError(err instanceof ApiError ? err.message : "Search failed"); }
    finally { setSearching(null); }
  }

  async function confirm() {
    if (!job) return;
    setBusy(true); setError(null);
    try { setJob(await api.post<PlaylistTransfer>(`/api/playlist-transfers/${job.id}/confirm`, destinationId ? { destinationPlaylistId: destinationId } : { newPlaylistName: newName })); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Could not start import"); }
    finally { setBusy(false); }
  }

  const working = job && ["queuedExtraction", "extracting", "queuedImport", "importing"].includes(job.status);
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 p-6 pb-32">
      <div><h1 className="flex items-center gap-3 text-3xl font-bold text-fg-primary"><ArrowRightLeft className="text-accent" /> Import Playlist</h1><p className="mt-1 text-sm text-fg-secondary">Transfer a public Apple Music playlist into your YouTube Music library.</p></div>
      {integration && (!integration.appleMusicConfigured || !integration.youtubeConfigured) && <p className="rounded-lg border border-danger/40 bg-danger/10 p-4 text-sm text-danger">Developer credentials are incomplete. Add the Apple Music and Google OAuth variables to the Docker environment.</p>}
      {integration && <section className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border-subtle bg-bg-elevated p-5"><div><h2 className="font-semibold text-fg-primary">YouTube account</h2><p className="text-sm text-fg-secondary">{integration.youtubeConnected ? `Connected as ${integration.youtubeChannelTitle ?? "your channel"}` : "Connect the account that owns the destination playlists."}</p></div>{integration.youtubeConnected ? <div className="flex items-center gap-3"><span className="flex items-center gap-2 text-sm text-accent"><Check size={16} /> Connected</span><Button size="sm" variant="ghost" onClick={disconnect} disabled={busy}>Disconnect</Button></div> : <Button onClick={connect} disabled={busy || !integration.youtubeConfigured}>Connect YouTube</Button>}</section>}

      {!job && <section className="flex flex-col gap-4 rounded-xl border border-border-subtle bg-bg-elevated p-5"><label className="text-sm text-fg-secondary">Source platform<select className="mt-1 h-11 w-full rounded-lg border border-border-subtle bg-bg-elevated-2 px-4 text-fg-primary"><option>Apple Music</option></select></label><label className="text-sm text-fg-secondary">Public playlist link<Input className="mt-1" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://music.apple.com/us/playlist/.../pl..." /></label><Button className="self-start" onClick={start} disabled={busy || !url.trim() || !integration?.youtubeConnected}>{busy ? <Loader2 className="animate-spin" size={16} /> : null} Extract songs</Button></section>}

      {working && <section className="rounded-xl border border-border-subtle bg-bg-elevated p-8 text-center"><Loader2 className="mx-auto mb-3 animate-spin text-accent" /><h2 className="font-semibold text-fg-primary">{job.status.includes("Import") || job.status === "importing" ? "Importing playlist" : "Extracting and matching songs"}</h2><p className="text-sm text-fg-secondary">{job.current} of {job.total || "…"}</p></section>}

      {job?.status === "readyForReview" && <>
        <section className="rounded-xl border border-border-subtle bg-bg-elevated p-5"><h2 className="text-xl font-semibold text-fg-primary">Review {job.source?.name}</h2><p className="text-sm text-fg-secondary">Replace ambiguous matches or skip tracks before importing.</p>{job.error && <p className="mt-3 rounded-lg bg-danger/10 p-3 text-sm text-danger">{job.error}</p>}</section>
        <div className="flex flex-col gap-3">{job.tracks.map((track, index) => <div key={`${track.appleTrackId}-${index}`} className="grid gap-3 rounded-xl border border-border-subtle bg-bg-elevated p-4 md:grid-cols-[1.2fr_1.5fr_auto]">
          <div><p className="font-medium text-fg-primary">{index + 1}. {track.title}</p><p className="text-sm text-fg-secondary">{track.artist} · {track.album || "Unknown album"} · {seconds(track.durationMs)}</p><span className="mt-2 inline-block rounded-full bg-bg-elevated-2 px-2 py-1 text-xs text-fg-secondary">{track.confidence}</span></div>
          <div>{track.skipped ? <p className="text-sm text-fg-muted">Skipped</p> : track.match ? <><a className="text-sm font-medium text-fg-primary hover:text-accent" href={`https://youtube.com/watch?v=${track.match.videoId}`} target="_blank" rel="noreferrer">{track.match.title} <ExternalLink className="inline" size={12} /></a><p className="text-xs text-fg-secondary">{track.match.channelTitle}</p></> : <p className="text-sm text-danger">No confident match</p>}
            {track.candidates.length > 0 && <select value={track.match?.videoId ?? ""} onChange={(e) => void updateTrack(index, e.target.value)} className="mt-2 h-9 w-full rounded-lg border border-border-subtle bg-bg-elevated-2 px-2 text-xs text-fg-primary"><option value="">Choose a result…</option>{track.candidates.map((candidate) => <option key={candidate.videoId} value={candidate.videoId}>{candidate.title} — {candidate.channelTitle}</option>)}</select>}</div>
          <div className="flex items-start gap-2"><Button size="sm" variant="outline" onClick={() => void findAlternatives(index)} disabled={searching === index}>{searching === index ? <Loader2 className="animate-spin" size={14} /> : <Search size={14} />} Replace</Button><Button size="sm" variant="ghost" onClick={() => void updateTrack(index, undefined, !track.skipped)}><SkipForward size={14} /> {track.skipped ? "Undo" : "Skip"}</Button></div>
        </div>)}</div>
        <section className="flex flex-col gap-4 rounded-xl border border-border-subtle bg-bg-elevated p-5"><h2 className="text-lg font-semibold text-fg-primary">Destination</h2><label className="text-sm text-fg-secondary">Existing YouTube playlist<select value={destinationId} onChange={(e) => setDestinationId(e.target.value)} className="mt-1 h-11 w-full rounded-lg border border-border-subtle bg-bg-elevated-2 px-4 text-fg-primary"><option value="">Create a new private playlist</option>{destinations.map((playlist) => <option key={playlist.id} value={playlist.id}>{playlist.name} ({playlist.privacyStatus})</option>)}</select></label>{!destinationId && <label className="text-sm text-fg-secondary">New playlist name<Input className="mt-1" value={newName} onChange={(e) => setNewName(e.target.value)} /></label>}<Button className="self-start" onClick={confirm} disabled={busy || (!destinationId && !newName.trim())}>Confirm import</Button></section>
      </>}

      {job?.status === "completed" && <section className="rounded-xl border border-accent/40 bg-accent-soft p-6"><h2 className="text-xl font-semibold text-fg-primary">Import complete</h2><p className="mt-2 text-sm text-fg-secondary">Added {job.result?.added ?? 0} · Duplicates {job.result?.duplicates ?? 0} · Skipped {job.result?.skipped ?? 0} · Unmatched {job.result?.unmatched ?? 0} · Failed {job.result?.failed ?? 0}</p><Button className="mt-4" variant="secondary" onClick={() => { setJob(null); setUrl(""); }}>Import another</Button></section>}
      {job?.status === "failed" && <section className="rounded-xl border border-danger/40 bg-danger/10 p-5"><h2 className="font-semibold text-danger">Transfer failed</h2><p className="text-sm text-fg-secondary">{job.error}</p><Button className="mt-3" variant="secondary" onClick={() => setJob(null)}>Start over</Button></section>}
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}
    </div>
  );
}
