"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { KeyRound, Loader2, RefreshCcw, Trash2, UserPlus, Copy, Check, DatabaseZap, Eye, EyeOff, RotateCw } from "lucide-react";
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
import type { ApiKey, ScanJob, User } from "@/lib/types";

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
  const { data: users, refetch } = useFetch<User[]>("/api/admin/users");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function createUser() {
    setError(null);
    try {
      await api.post("/api/admin/users", { username, password, role: "user" });
      setUsername("");
      setPassword("");
      refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create user");
    }
  }

  async function toggleActive(user: User) {
    await api.patch(`/api/admin/users/${user.id}/active?is_active=${!user.isActive}`);
    refetch();
  }

  async function deleteUser(user: User) {
    await api.delete(`/api/admin/users/${user.id}`);
    refetch();
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
          <label className="mb-1 block text-xs text-fg-secondary">Password</label>
          <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-48" />
        </div>
        <Button onClick={createUser}>
          <UserPlus size={16} /> Add user
        </Button>
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}

      <div className="flex flex-col gap-2">
        {(users ?? []).map((user) => (
          <div key={user.id} className="flex items-center justify-between rounded-lg bg-bg-elevated px-4 py-3">
            <div>
              <p className="text-sm font-medium text-fg-primary">
                {user.username} <span className="text-xs text-fg-muted">({user.role})</span>
              </p>
              <p className="text-xs text-fg-muted">{user.isActive ? "Active" : "Disabled"}</p>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={() => toggleActive(user)} className="text-xs text-fg-secondary hover:text-fg-primary">
                {user.isActive ? "Disable" : "Enable"}
              </button>
              <button onClick={() => deleteUser(user)} className="text-fg-secondary hover:text-danger" aria-label="Delete user">
                <Trash2 size={16} />
              </button>
            </div>
          </div>
        ))}
      </div>
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
          <AdminUsersSection />
        </>
      )}
    </div>
  );
}
