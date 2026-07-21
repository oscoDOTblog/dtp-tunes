# V1 scope and limitations

## In scope

- Self-hosted single-server deployment via `docker compose up`.
- Web playback via the Next.js app (Home, Search, Library, Artist, Album,
  Playlist, Queue, Settings/Admin), with a persistent queue, native
  `HTMLAudioElement` playback, and Media Session integration.
- OpenSubsonic-compatible REST layer for a practical baseline of
  system/browse/search/user-state/media endpoints (see
  [`docs/SUBSONIC_COMPATIBILITY.md`](SUBSONIC_COMPATIBILITY.md)).
- MongoDB-backed catalog built by a filesystem scanner (Mutagen for tags,
  Pillow for artwork), with periodic and on-demand rescans.
- Byte-range file streaming and on-demand, concurrency-limited FFmpeg
  transcoding (`mp3`/`opus` targets).
- Argon2id web passwords, cookie sessions, revocable API keys, and a
  documented (imperfect but necessary) legacy Subsonic credential scheme.
- Basic admin: create/disable/delete users, trigger scans, view scan status.

## Explicitly out of scope for V1

- **Podcasts, video, chat, sharing, and internet radio** Subsonic endpoint
  families — not implemented; clients that require them will show those
  features as unavailable.
- **Jukebox mode** (server-side playback control) — not implemented.
- **Precomputed/cached transcodes** — every transcode is generated live and
  discarded; there's no transcode cache or format pre-warming.
- **Hardware-accelerated transcoding** — FFmpeg runs in software (CPU) only.
- **ReplayGain / loudness normalization.**
- **True gapless playback** — the native `<audio>` element does not
  guarantee sample-accurate gapless transitions between tracks.
- **Audio fingerprinting** — song identity is the file's relative path, so
  files renamed or moved outside the app (not through a rescan-detected
  delete+add) are treated as new songs and lose star/play-history
  continuity. A fingerprinting-based identity strategy is future work.
- **Multi-node / distributed deployment** — this is a single-server
  Compose stack; MongoDB, the music volume, and the artwork cache are not
  designed to be shared across multiple API/worker hosts in V1.
- **Fine-grained sharing/collaboration** (shared playlists beyond a simple
  `public` flag, per-track permissions, etc.).

## Known operational gaps to resolve before wider release

- **Client compatibility is a target, not a guarantee.** Protocol
  conformance and the fixture tests in `api/tests` reduce risk, but every
  real Subsonic client has its own quirks; treat the matrix in
  [`docs/SUBSONIC_COMPATIBILITY.md`](SUBSONIC_COMPATIBILITY.md) as "tested",
  not "supported everywhere."
- **Backups.** MongoDB (the `mongodb-data` volume) and the `cache/` artwork
  directory should be backed up; `music/` remains the operator's own
  responsibility and is never written to by this app (mounted read-only).
- **HTTPS.** Run dtp-tunes behind TLS for anything reachable outside a
  trusted LAN — this matters even more if legacy Subsonic password
  authentication is enabled for older clients, since that scheme sends a
  recoverable credential.
- **Single point of transcoding capacity.** `FFMPEG_MAX_CONCURRENT` caps
  concurrent live transcodes per `api` container; size it to your CPU and
  expected concurrent transcoding clients (direct-play clients don't count
  against this limit).
