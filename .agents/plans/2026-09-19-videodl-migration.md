# Integrate VideoDL workflows into dtp-tunes

## Summary

Add an admin-only “Add Music” area to Tunes with URL downloads, one-off track review, a background queue, job history, and direct MP3 upload. Use Tunes login, MongoDB, and library scanning. Leave the existing VideoDL app and its queue/history untouched. Do not bring over cookie upload or dtp-os cookie sync yet; sources requiring cookies may fail until that integration returns.

## Implementation

- Add admin navigation and Tunes-styled pages for URL metadata and cover review, one-off download progress and track reordering/renaming, queue management (cancel, retry, remove, clear), and MP3 upload with optional album metadata and cover.
- Add admin-only Tunes APIs under `/api/admin/ingest` for metadata, jobs, review/save, queue actions, upload, and library write-status checks. Never return host paths, cookie data, or internal manifests to browsers.
- Port VideoDL’s yt-dlp, tagging, artwork, and upload behavior into Tunes services. Replace VideoDL’s SQLite queue with a dedicated MongoDB job collection using atomic leases, bounded concurrency, cancellation, restart recovery, and durable progress/history. Run a separate private ingestion-worker container using the Tunes API image; share a persistent staging volume with the API.
- Save into the shared `/music` tree using safe staged writes. Merge into existing albums: replace matching audio files, but preserve unrelated tracks and existing lyric sidecars. Enqueue a Tunes scan directly after a successful save or upload; report scan failure separately from an already-successful file save.
- Keep VideoDL’s current deployment, URL, queue database, and staged jobs unchanged. Do not port its legacy ZIP/download endpoints or cookie endpoints, since they are not part of its current UI workflows.

## Permissions and Deployment

- Keep Tunes API and ingestion worker non-root. On `rath`, configure them for the intended Linux account (`1000:1003`), not the Mac’s `501:20`.
- Grant that account write/traverse ACLs on existing music directories and default ACLs on the library root and artist/album directories. Verify inheritance for folders created both by VideoDL’s normal `mkdir` path and its staging-directory rename path. Do not change library ownership or use world-writable permissions.
- Mount `/music` read-write for the Tunes API (uploads and lyrics) and ingestion worker; keep the scanner’s mount read-only. Add a persistent staging volume and update the nginx upload limit so VideoDL’s current MP3-upload limits can pass through Tunes.
- Provide a `rath` deployment runbook covering ACL application, permission probes on an existing root-owned album, Compose recreation, and rollback. Do not automatically alter the host library during application startup.

## Tests and Acceptance

- Admins can complete both URL workflows and MP3 upload inside Tunes; ordinary users cannot access their pages or APIs.
- Jobs survive API/worker restarts, do not run twice, and support progress, cancel, retry, review, and history cleanup.
- Saving to an existing album preserves unrelated tracks and `.txt` lyrics. Newly created VideoDL folders remain writable by Tunes through inherited ACLs.
- Uploaded files and completed jobs become visible in the Tunes library after scan; a scan error does not falsely mark the file write as failed.
- Test unsafe paths, invalid uploads, limits, yt-dlp failures, filesystem permission failures, and concurrent saves. Run backend tests, frontend lint/typecheck/build, Compose validation, and an end-to-end staging deployment check before switching daily usage.

## Assumptions

- “Full migration” means full **workflow parity**, not transfer of VideoDL’s existing jobs or history.
- VideoDL remains running and usable against the shared library.
- No YouTube cookie handling is included in this phase.
- Tunes’ ingestion queue uses MongoDB; disk staging is persistent but not the queue’s source of truth.