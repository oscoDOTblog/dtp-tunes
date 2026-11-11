"use client";

import { useEffect, useState, useSyncExternalStore, type FormEvent } from "react";
import { KeyRound, Loader2, RefreshCcw, Trash2, UserPlus, Copy, Check, DatabaseZap, Eye, EyeOff, RotateCw, Combine } from "lucide-react";
import { useAuth } from "@/lib/useAuth";
import { useFetch } from "@/lib/useFetch";
import { api, ApiError } from "@/lib/api";
import {
  ACCENT_TONES,
  applyAccent,
  getServerAccent,
  getStoredAccent,
  subscribeAccent,
  type AccentTone,
} from "@/lib/accent";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import type { Album, ApiKey, ScanJob, Song, User } from "@/lib/types";

function AppearanceSection() {
  const accent = useSyncExternalStore(subscribeAccent, getStoredAccent, getServerAccent);

  function selectTone(tone: AccentTone) {
    applyAccent(tone);
  }

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold text-fg-primary">Appearance</h2>
      <p className="text-sm text-fg-secondary">Pick an accent color for this device.</p>
      <div className="flex flex-wrap gap-3">
        {ACCENT_TONES.map((tone) => {
          const selected = accent === tone.id;
          return (
            <button
              key={tone.id}
              onClick={() => selectTone(tone.id)}
              aria-pressed={selected}
              className={`flex items-center gap-2 rounded-full border px-4 py-2 text-sm transition-colors ${
                selected
                  ? "border-accent bg-accent-soft text-fg-primary"
                  : "border-border-subtle bg-bg-elevated text-fg-secondary hover:bg-bg-hover"
              }`}
            >
              <span
                aria-hidden
                className="h-4 w-4 rounded-full"
                style={{ backgroundColor: tone.swatch }}
              />
              {tone.label}
              {selected && <Check size={14} className="text-accent" />}
            </button>
          );
        })}
      </div>
    </section>
  );
}

function SubsonicPasswordSection() {
  const { user } = useAuth();
  const [password, setPassword] = useState<string | null>(null);
  const [visible, setVisible] = useState(false);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  async function reveal() {
    setLoading(true);
    setError(null);
    setNote(null);
    try {
      const result = await api.get<{ username: string; password: string }>("/api/auth/subsonic-password");
      setPassword(result.password);
      setVisible(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to reveal Subsonic password");
    } finally {
      setLoading(false);
    }
  }

  async function rotate() {
    const confirmed = window.confirm(
      "Rotate your Subsonic client password?\n\nExisting Subsonic / OpenSubsonic clients will stop working until you update them with the new password. Your web login password is unchanged.",
    );
    if (!confirmed) return;

    setLoading(true);
    setError(null);
    setNote(null);
    try {
      const result = await api.post<{ username: string; password: string }>("/api/auth/subsonic-password/rotate");
      setPassword(result.password);
      setVisible(true);
      setNote("New Subsonic password generated. Update your clients now.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to rotate Subsonic password");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold text-fg-primary">Subsonic client password</h2>
      <p className="text-sm text-fg-secondary">
        Most Subsonic apps (DSub, Symfonium, Amperfy, etc.) need your <strong className="font-medium text-fg-primary">web
        username</strong> plus this separate client password — not your web login password.
        {user?.username ? (
          <>
            {" "}
            Your username is <code className="text-fg-primary">{user.username}</code>.
          </>
        ) : null}
      </p>

      {password && (
        <div className="flex items-center gap-2 rounded-lg bg-accent-soft p-3 text-sm text-fg-primary">
          <code className="flex-1 break-all">{visible ? password : "••••••••••••••••••••••••"}</code>
          <button
            type="button"
            onClick={() => setVisible((v) => !v)}
            aria-label={visible ? "Hide password" : "Show password"}
            className="text-fg-secondary hover:text-fg-primary"
          >
            {visible ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
          <button
            type="button"
            onClick={() => {
              navigator.clipboard.writeText(password);
              setCopied(true);
              setTimeout(() => setCopied(false), 1500);
            }}
            aria-label="Copy password"
            className="text-fg-secondary hover:text-fg-primary"
          >
            {copied ? <Check size={16} /> : <Copy size={16} />}
          </button>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <Button onClick={reveal} disabled={loading} variant="secondary">
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Eye size={16} />}
          {password ? "Refresh" : "Reveal password"}
        </Button>
        <Button onClick={rotate} disabled={loading} variant="outline">
          <RotateCw size={16} />
          Rotate
        </Button>
      </div>
      {note && <p className="text-sm text-fg-primary">{note}</p>}
      {error && <p className="text-sm text-danger">{error}</p>}
    </section>
  );
}

function ApiKeysSection() {
  const { data: keys, refetch } = useFetch<ApiKey[]>("/api/api-keys");
  const [name, setName] = useState("");
  const [newKey, setNewKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function createKey() {
    if (!name.trim()) return;
    const created = await api.post<ApiKey & { fullKey: string }>("/api/api-keys", { name: name.trim() });
    setNewKey(created.fullKey);
    setName("");
    refetch();
  }

  async function revoke(id: string) {
    await api.delete(`/api/api-keys/${id}`);
    refetch();
  }

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold text-fg-primary">Subsonic API keys</h2>
      <p className="text-sm text-fg-secondary">
        Use an API key with legacy Subsonic clients that support key-based auth, instead of your account password.
      </p>

      {newKey && (
        <div className="flex items-center gap-2 rounded-lg bg-accent-soft p-3 text-sm text-fg-primary">
          <code className="flex-1 truncate">{newKey}</code>
          <button
            onClick={() => {
              navigator.clipboard.writeText(newKey);
              setCopied(true);
              setTimeout(() => setCopied(false), 1500);
            }}
          >
            {copied ? <Check size={16} /> : <Copy size={16} />}
          </button>
        </div>
      )}

      <div className="flex max-w-md gap-2">
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Key name (e.g. DSub)" />
        <Button onClick={createKey}>
          <KeyRound size={16} /> Create
        </Button>
      </div>

      <div className="flex flex-col gap-2">
        {(keys ?? []).map((key) => (
          <div key={key.id} className="flex items-center justify-between rounded-lg bg-bg-elevated px-4 py-3">
            <div>
              <p className="text-sm font-medium text-fg-primary">{key.name}</p>
              <p className="text-xs text-fg-muted">Created {new Date(key.createdAt).toLocaleDateString()}</p>
            </div>
            <button onClick={() => revoke(key.id)} className="text-fg-secondary hover:text-danger" aria-label="Revoke key">
              <Trash2 size={16} />
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}

function AdminUsersSection() {
  const { user: currentUser } = useAuth();
  const { data: users, refetch } = useFetch<User[]>("/api/admin/users");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [newRole, setNewRole] = useState<"admin" | "user">("user");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [resetFor, setResetFor] = useState<string | null>(null);
  const [resetPassword, setResetPassword] = useState("");

  async function createUser() {
    setError(null);
    setNotice(null);
    try {
      await api.post("/api/admin/users", { username, password, role: newRole });
      setUsername("");
      setPassword("");
      setNewRole("user");
      refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create user");
    }
  }

  async function toggleActive(user: User) {
    setError(null);
    setNotice(null);
    try {
      await api.patch(`/api/admin/users/${user.id}/active?is_active=${!user.isActive}`);
      refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update user");
    }
  }

  async function changeRole(user: User) {
    setError(null);
    setNotice(null);
    try {
      await api.patch(`/api/admin/users/${user.id}/role?role=${user.role === "admin" ? "user" : "admin"}`);
      setNotice(`${user.username} is now ${user.role === "admin" ? "a user" : "an admin"}.`);
      refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to change role");
    }
  }

  async function resetUserPassword(user: User) {
    setError(null);
    setNotice(null);
    try {
      await api.patch(`/api/admin/users/${user.id}/password`, { password: resetPassword });
      setNotice(
        user.id === currentUser?.id
          ? `Password updated for ${user.username}.`
          : `Password updated for ${user.username}. They were signed out and must log in again.`,
      );
      setResetFor(null);
      setResetPassword("");
      refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to reset password");
    }
  }

  async function deleteUser(user: User) {
    setError(null);
    setNotice(null);
    try {
      await api.delete(`/api/admin/users/${user.id}`);
      refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete user");
    }
  }

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold text-fg-primary">Users</h2>

      <div className="flex flex-wrap items-end gap-2">
        <div>
          <label className="mb-1 block text-xs text-fg-secondary">Username</label>
          <Input value={username} onChange={(e) => setUsername(e.target.value)} className="w-48" />
        </div>
        <div>
          <label className="mb-1 block text-xs text-fg-secondary">Password (min 8 chars)</label>
          <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-48" />
        </div>
        <div>
          <label className="mb-1 block text-xs text-fg-secondary">Role</label>
          <select
            value={newRole}
            onChange={(e) => setNewRole(e.target.value === "admin" ? "admin" : "user")}
            className="h-11 rounded-lg border border-border-subtle bg-bg-elevated-2 px-3 text-sm text-fg-primary outline-none focus:border-accent"
          >
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        <Button onClick={createUser}>
          <UserPlus size={16} /> Add user
        </Button>
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      {notice && <p className="text-sm text-fg-primary">{notice}</p>}

      <div className="flex flex-col gap-2">
        {(users ?? []).map((user) => {
          const isSelf = user.id === currentUser?.id;
          return (
            <div key={user.id} className="flex flex-col gap-2 rounded-lg bg-bg-elevated px-4 py-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-fg-primary">
                    {user.username} <span className="text-xs text-fg-muted">({user.role})</span>
                  </p>
                  <p className="text-xs text-fg-muted">{user.isActive ? "Active" : "Disabled"}</p>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => changeRole(user)}
                    disabled={isSelf}
                    title={isSelf ? "You cannot change your own role" : user.role === "admin" ? "Demote to user" : "Promote to admin"}
                    className="text-xs text-fg-secondary hover:text-fg-primary disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {user.role === "admin" ? "Make user" : "Make admin"}
                  </button>
                  <button onClick={() => toggleActive(user)} className="text-xs text-fg-secondary hover:text-fg-primary">
                    {user.isActive ? "Disable" : "Enable"}
                  </button>
                  <button
                    onClick={() => {
                      setError(null);
                      setNotice(null);
                      setResetFor(resetFor === user.id ? null : user.id);
                      setResetPassword("");
                    }}
                    className="text-xs text-fg-secondary hover:text-fg-primary"
                  >
                    {resetFor === user.id ? "Cancel" : "Reset password"}
                  </button>
                  <button
                    onClick={() => deleteUser(user)}
                    disabled={isSelf}
                    title={isSelf ? "You cannot delete your own account" : "Delete user"}
                    className="text-fg-secondary hover:text-danger disabled:cursor-not-allowed disabled:opacity-40"
                    aria-label="Delete user"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
              {resetFor === user.id && (
                <div className="flex flex-wrap items-end gap-2">
                  <div>
                    <label className="mb-1 block text-xs text-fg-secondary">
                      New password for {user.username} (min 8 chars)
                    </label>
                    <Input
                      type="password"
                      value={resetPassword}
                      onChange={(e) => setResetPassword(e.target.value)}
                      className="w-56"
                    />
                  </div>
                  <Button onClick={() => resetUserPassword(user)} disabled={resetPassword.length < 8}>
                    <KeyRound size={16} /> Set password
                  </Button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function albumLabel(album: Album): string {
  return `${album.artistName ?? "Unknown Artist"} — ${album.name} (${album.songCount} song${album.songCount === 1 ? "" : "s"})`;
}

function AdminAlbumMergeSection() {
  const { data: albums, refetch } = useFetch<Album[]>("/api/albums?limit=200&sort=name");
  const [sourceId, setSourceId] = useState("");
  const [targetId, setTargetId] = useState("");
  const [merging, setMerging] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const source = albums?.find((album) => album.id === sourceId);
  const target = albums?.find((album) => album.id === targetId);

  async function merge() {
    if (!source || !target || source.id === target.id) return;
    const confirmed = window.confirm(
      `Merge “${source.name}” by ${source.artistName ?? "Unknown Artist"} into “${target.name}” by ${target.artistName ?? "Unknown Artist"}?\n\n` +
      `${source.songCount} song${source.songCount === 1 ? "" : "s"} will move to the destination album and the source album will be removed. Audio files, playlists, history, and song IDs are preserved.`,
    );
    if (!confirmed) return;

    setMerging(true);
    setMessage(null);
    setError(null);
    try {
      const result = await api.post<{ movedSongs: number }>("/api/admin/albums/merge", {
        sourceAlbumId: source.id,
        targetAlbumId: target.id,
      });
      setMessage(`Merged ${result.movedSongs} song${result.movedSongs === 1 ? "" : "s"} into “${target.name}”.`);
      setSourceId("");
      setTargetId("");
      refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to merge albums");
    } finally {
      setMerging(false);
    }
  }

  const selectClass = "h-11 w-full rounded-lg border border-border-subtle bg-bg-elevated-2 px-3 text-sm text-fg-primary outline-none focus:border-accent";

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold text-fg-primary">Merge albums</h2>
      <p className="text-sm text-fg-secondary">
        Move every song from one album into another and remove the empty source album. The destination album&apos;s name and metadata take precedence.
      </p>
      <div className="grid max-w-3xl gap-4 md:grid-cols-[1fr_auto_1fr] md:items-end">
        <label className="flex flex-col gap-1 text-xs text-fg-secondary">
          Source album (removed)
          <select className={selectClass} value={sourceId} onChange={(event) => setSourceId(event.target.value)}>
            <option value="">Choose source…</option>
            {(albums ?? []).map((album) => <option key={album.id} value={album.id}>{albumLabel(album)}</option>)}
          </select>
        </label>
        <span className="hidden pb-3 text-fg-muted md:block">→</span>
        <label className="flex flex-col gap-1 text-xs text-fg-secondary">
          Destination album (kept)
          <select className={selectClass} value={targetId} onChange={(event) => setTargetId(event.target.value)}>
            <option value="">Choose destination…</option>
            {(albums ?? []).filter((album) => album.id !== sourceId).map((album) => <option key={album.id} value={album.id}>{albumLabel(album)}</option>)}
          </select>
        </label>
      </div>
      <Button className="w-fit" onClick={merge} disabled={merging || !source || !target || source.id === target.id}>
        {merging ? <Loader2 size={16} className="animate-spin" /> : <Combine size={16} />}
        {merging ? "Merging…" : "Merge albums"}
      </Button>
      {message && <p className="text-sm text-fg-primary">{message}</p>}
      {error && <p className="text-sm text-danger">{error}</p>}
    </section>
  );
}

interface AlbumDetail {
  album: Album;
  songs: Song[];
}

function optionalNumber(value: string): number | null {
  return value.trim() ? Number(value) : null;
}

function AdminMetadataEditorSection() {
  const { data: albums, refetch: refetchAlbums } = useFetch<Album[]>("/api/albums?limit=200&sort=name");
  const [albumId, setAlbumId] = useState("");
  const { data, refetch } = useFetch<AlbumDetail>(albumId ? `/api/albums/${albumId}` : null, [albumId]);
  const [songId, setSongId] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const song = data?.songs.find((item) => item.id === songId);

  async function saveAlbum(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!data) return;
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") ?? "").trim();
    if (!name) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      await api.patch(`/api/admin/albums/${data.album.id}`, {
        name,
        year: optionalNumber(String(form.get("year") ?? "")),
        genre: String(form.get("genre") ?? "").trim() || null,
      });
      setMessage("Album information saved.");
      refetch();
      refetchAlbums();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save album information");
    } finally {
      setSaving(false);
    }
  }

  async function saveSong(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!song) return;
    const form = new FormData(event.currentTarget);
    const title = String(form.get("title") ?? "").trim();
    if (!title) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      await api.patch(`/api/admin/songs/${song.id}`, {
        title,
        artistName: String(form.get("artistName") ?? "").trim() || null,
        year: optionalNumber(String(form.get("year") ?? "")),
        genre: String(form.get("genre") ?? "").trim() || null,
        track: optionalNumber(String(form.get("track") ?? "")),
        discNumber: optionalNumber(String(form.get("discNumber") ?? "")),
      });
      setMessage("Song information saved.");
      refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save song information");
    } finally {
      setSaving(false);
    }
  }

  const selectClass = "h-11 w-full rounded-lg border border-border-subtle bg-bg-elevated-2 px-3 text-sm text-fg-primary outline-none focus:border-accent";
  const fieldClass = "flex flex-col gap-1 text-xs text-fg-secondary";

  return (
    <section className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold text-fg-primary">Edit library information</h2>
        <p className="mt-1 text-sm text-fg-secondary">Edit catalog metadata without changing song IDs, files, playlists, or listening history.</p>
      </div>
      <label className={`${fieldClass} max-w-2xl`}>
        Album
        <select className={selectClass} value={albumId} onChange={(event) => { setAlbumId(event.target.value); setSongId(""); }}>
          <option value="">Choose an album…</option>
          {(albums ?? []).map((album) => <option key={album.id} value={album.id}>{albumLabel(album)}</option>)}
        </select>
      </label>

      {data && (
        <form key={`${data.album.id}-${data.album.name}-${data.album.year}-${data.album.genre}`} onSubmit={saveAlbum} className="flex max-w-3xl flex-col gap-4 rounded-lg border border-border-subtle bg-bg-elevated p-4">
          <h3 className="text-sm font-semibold text-fg-primary">Album information</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className={fieldClass}>Name<Input name="name" defaultValue={data.album.name} required /></label>
            <label className={fieldClass}>Year<Input name="year" type="number" min="1" max="9999" defaultValue={data.album.year ?? ""} /></label>
            <label className={fieldClass}>Genre<Input name="genre" defaultValue={data.album.genre ?? ""} /></label>
            <label className={fieldClass}>Album artist<Input defaultValue={data.album.artistName ?? ""} disabled title="Album artist editing is not yet supported" /></label>
          </div>
          <Button type="submit" className="w-fit" disabled={saving}>
            {saving && <Loader2 size={16} className="animate-spin" />} Save album
          </Button>
        </form>
      )}

      {data && data.songs.length > 0 && (
        <div className="flex max-w-3xl flex-col gap-4 rounded-lg border border-border-subtle bg-bg-elevated p-4">
          <h3 className="text-sm font-semibold text-fg-primary">Song information</h3>
          <label className={fieldClass}>
            Song
            <select className={selectClass} value={songId} onChange={(event) => setSongId(event.target.value)}>
              <option value="">Choose a song…</option>
              {data.songs.map((item) => <option key={item.id} value={item.id}>{item.track ? `${item.track}. ` : ""}{item.title}</option>)}
            </select>
          </label>
          {song && (
            <form key={`${song.id}-${song.title}-${song.artistName}-${song.year}-${song.genre}-${song.track}-${song.discNumber}`} onSubmit={saveSong} className="flex flex-col gap-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <label className={fieldClass}>Title<Input name="title" defaultValue={song.title} required /></label>
                <label className={fieldClass}>Artist<Input name="artistName" defaultValue={song.artistName ?? ""} /></label>
                <label className={fieldClass}>Year<Input name="year" type="number" min="1" max="9999" defaultValue={song.year ?? ""} /></label>
                <label className={fieldClass}>Genre<Input name="genre" defaultValue={song.genre ?? ""} /></label>
                <label className={fieldClass}>Track number<Input name="track" type="number" min="1" defaultValue={song.track ?? ""} /></label>
                <label className={fieldClass}>Disc number<Input name="discNumber" type="number" min="1" defaultValue={song.discNumber ?? ""} /></label>
              </div>
              <Button type="submit" className="w-fit" disabled={saving}>
                {saving && <Loader2 size={16} className="animate-spin" />} Save song
              </Button>
            </form>
          )}
        </div>
      )}
      {message && <p className="text-sm text-fg-primary">{message}</p>}
      {error && <p className="text-sm text-danger">{error}</p>}
    </section>
  );
}

const SCAN_POLL_INTERVAL_MS = 2000;

function AdminScanSection() {
  const { data: jobs, refetch } = useFetch<ScanJob[]>("/api/admin/scan-jobs");
  const latest = jobs?.[0];
  const scanning = latest?.status === "pending" || latest?.status === "running";
  const [resetting, setResetting] = useState(false);
  const [resetMessage, setResetMessage] = useState<string | null>(null);
  const [resetError, setResetError] = useState<string | null>(null);

  // Poll while a scan is active so counts and status update live.
  useEffect(() => {
    if (!scanning) return;
    const interval = setInterval(refetch, SCAN_POLL_INTERVAL_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scanning]);

  async function triggerScan() {
    await api.post("/api/admin/scan-jobs");
    refetch();
  }

  async function resetLibrary() {
    const confirmed = window.confirm(
      "Reset the library database?\n\nThis deletes all artists, albums, songs, genres, stars, play history, and cover cache. Playlists are emptied. Users and API keys are kept. A fresh scan will start immediately.",
    );
    if (!confirmed) return;

    setResetting(true);
    setResetMessage(null);
    setResetError(null);
    try {
      const result = await api.post<{
        songs: number;
        albums: number;
        artists: number;
        coversCleared: number;
        rescanEnqueued: boolean;
      }>("/api/admin/reset-library?rescan=true");
      setResetMessage(
        `Cleared ${result.artists} artists, ${result.albums} albums, ${result.songs} songs` +
          (result.coversCleared ? `, ${result.coversCleared} covers` : "") +
          (result.rescanEnqueued ? ". Rescan started." : "."),
      );
      refetch();
    } catch (err) {
      setResetError(err instanceof ApiError ? err.message : "Failed to reset library");
    } finally {
      setResetting(false);
    }
  }

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold text-fg-primary">Library scan</h2>
      <p className="text-sm text-fg-secondary">
        Scans the mounted <code>/music</code> folder for new, changed, and removed files.
      </p>
      <Button onClick={triggerScan} className="w-fit" disabled={scanning || resetting}>
        <RefreshCcw size={16} className={scanning ? "animate-spin" : undefined} />
        {scanning ? "Scanning…" : "Start scan now"}
      </Button>
      {latest && (
        <div className="rounded-lg bg-bg-elevated p-4 text-sm text-fg-secondary">
          <p className="flex items-center gap-2">
            Status:{" "}
            <span className={scanning ? "flex items-center gap-2 text-accent" : "text-fg-primary"}>
              {scanning && <Loader2 size={14} className="animate-spin" aria-hidden />}
              {latest.status}
            </span>
          </p>
          <p>Scanned: {latest.scannedCount} · Added: {latest.addedCount} · Updated: {latest.updatedCount} · Removed: {latest.removedCount}</p>
          {latest.lastError && <p className="text-danger">Error: {latest.lastError}</p>}
        </div>
      )}

      <div className="mt-2 flex flex-col gap-3 rounded-lg border border-danger/40 bg-bg-elevated p-4">
        <h3 className="text-sm font-semibold text-fg-primary">Reset library database</h3>
        <p className="text-sm text-fg-secondary">
          Wipe scanned catalog metadata after remounting a different music folder. Does not delete
          users, sessions, or API keys. Playlist song lists are emptied.
        </p>
        <Button
          variant="outline"
          className="w-fit border-danger/60 text-danger hover:border-danger hover:bg-danger/10"
          onClick={resetLibrary}
          disabled={resetting || scanning}
        >
          {resetting ? <Loader2 size={16} className="animate-spin" /> : <DatabaseZap size={16} />}
          {resetting ? "Resetting…" : "Reset library DB"}
        </Button>
        {resetMessage && <p className="text-sm text-fg-primary">{resetMessage}</p>}
        {resetError && <p className="text-sm text-danger">{resetError}</p>}
      </div>
    </section>
  );
}

export default function SettingsPage() {
  const { user } = useAuth();

  return (
    <div className="flex flex-col gap-10 p-6 pb-32">
      <h1 className="text-2xl font-bold text-fg-primary">Settings</h1>
      <AppearanceSection />
      <hr className="border-border-subtle" />
      <SubsonicPasswordSection />
      <hr className="border-border-subtle" />
      <ApiKeysSection />
      {user?.role === "admin" && (
        <>
          <hr className="border-border-subtle" />
          <AdminScanSection />
          <hr className="border-border-subtle" />
          <AdminAlbumMergeSection />
          <hr className="border-border-subtle" />
          <AdminMetadataEditorSection />
          <hr className="border-border-subtle" />
          <AdminUsersSection />
        </>
      )}
    </div>
  );
}
