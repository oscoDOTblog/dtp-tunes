# dtp-tunes

A self-hosted music server: a Spotify-inspired Next.js web player, a FastAPI
backend, MongoDB metadata, a read-only music library volume, on-demand FFmpeg
transcoding, and a deliberately scoped [OpenSubsonic](https://opensubsonic.netlify.app/docs/api-reference/)
compatibility layer so existing Subsonic-family apps (DSub, Substreamer,
play:Sub, Amperfy, etc.) can connect too.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for how the pieces fit
together, [`docs/V1_SCOPE.md`](docs/V1_SCOPE.md) for what's in/out of scope,
[`docs/SUBSONIC_COMPATIBILITY.md`](docs/SUBSONIC_COMPATIBILITY.md) for the
tested endpoint/client matrix, and
[`docs/RUNTIPI_DEPLOYMENT.md`](docs/RUNTIPI_DEPLOYMENT.md) for putting the
stack behind Runtipi Traefik on a public custom domain.

## Services

| Service   | Description                                                                 |
| --------- | ---------------------------------------------------------------------------- |
| `gateway` | nginx — the one public origin; routes `/`, `/api`, `/rest` without buffering media |
| `web`     | Next.js Spotify-inspired frontend (standalone build)                        |
| `api`     | FastAPI — JSON web APIs, OpenSubsonic REST, streaming, cover art, transcoding |
| `worker`  | same image as `api`, runs the leased library scanner instead of the HTTP server |
| `mongodb` | optional bundled metadata store — off by default; enable with `--profile bundled-db` (external `MONGODB_URI` used otherwise) |

## Quick start

1. Copy the example environment file and edit the secrets:

   ```bash
   cp .env.example .env
   ```

   At minimum, change `ADMIN_PASSWORD` and `APP_ENCRYPTION_KEY` (32+ random
   bytes — used for session cookies and the reversible Subsonic-compat
   credential described in [`docs/SUBSONIC_COMPATIBILITY.md`](docs/SUBSONIC_COMPATIBILITY.md)).
   Generate one with:

   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. Copy your music into `./music` (read-only bind mount — see
   [`music/README.md`](music/README.md) for supported formats and permission
   notes). An empty folder is fine to start; you can scan again later.

3. Point `MONGODB_URI` at your MongoDB. By default the stack uses an
   **external** database (e.g. Atlas) and does not start a local Mongo
   container. To run a bundled Mongo instead (x86 hosts only — `mongo:7`
   does not run on a Raspberry Pi 4), set `MONGODB_URI=mongodb://mongodb:27017`
   and enable the `bundled-db` profile in the next step.

4. Start everything:

   ```bash
   # external MongoDB (default)
   docker compose up --build

   # or, with the bundled Mongo container
   docker compose --profile bundled-db up --build
   ```

5. Open [http://127.0.0.1:8080](http://127.0.0.1:8080) and sign in with
   `ADMIN_USERNAME` / `ADMIN_PASSWORD` from `.env` (created automatically on
   first boot — bootstrap only runs once, when the `users` collection is
   empty). The gateway binds to loopback only (`127.0.0.1:8080`) so it is not
   reachable from the LAN unless you put Traefik (or another proxy) in front.

6. From **Settings → Library scan**, trigger a scan (one also runs
   automatically shortly after the worker starts, and on the interval set by
   `SCAN_INTERVAL_SECONDS`).

## Deploy behind Runtipi (custom domain)

On a host that already runs [Runtipi](https://runtipi.io), reuse Traefik for
HTTPS instead of publishing dtp-tunes on the LAN. This stack stays
**standalone** — do not use the Runtipi dashboard “Expose app” UI.

1. Set `DTP_TUNES_DOMAIN` (and secrets) in `.env`.
2. Point a DNS **A** record at your public IP; forward router ports **80/443**
   to the Runtipi host. Keep Cloudflare DNS-only for this hostname if you use
   Cloudflare.
3. Start with both Compose files:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.runtipi.yml up -d --build
   ```

4. Open `https://<DTP_TUNES_DOMAIN>/`. Subsonic clients use the same base URL.

Full checklist, networking, troubleshooting, and rollback:
[`docs/RUNTIPI_DEPLOYMENT.md`](docs/RUNTIPI_DEPLOYMENT.md).

## Local development (without Docker)

Backend:

```bash
cd api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export $(grep -v '^#' ../.env | xargs)  # or use a .env in api/
uvicorn app.main:app --reload
# in another shell, run the scanner worker:
python -m app.worker.main
```

Frontend:

```bash
cd web
npm install
NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev
```

You'll also need a local MongoDB instance (`docker run -p 27017:27017 mongo:7`
works well) and `ffmpeg`/`ffprobe` on your `PATH` for transcoding.

## Tests

```bash
cd api
pip install -r requirements.txt
ruff check app tests
pytest
```

```bash
cd web
npm run lint
npm run typecheck
npm run build
```

## Backups

MongoDB holds all metadata (users, catalog, playlists, play history, scan
jobs) — back it up regularly. With an external database (e.g. Atlas), use that
provider's backups; with the bundled `bundled-db` profile, back up the
`mongodb-data` volume. The generated cover-art
cache (`./cache`) can be regenerated by rescanning if lost. Your source music
library (`./music`) is not managed by this app and remains your own backup
responsibility.

## Security notes

- Put dtp-tunes behind HTTPS if it's reachable outside a trusted LAN,
  especially if you enable legacy Subsonic password authentication for older
  clients. See [`docs/SUBSONIC_COMPATIBILITY.md`](docs/SUBSONIC_COMPATIBILITY.md).
- `APP_ENCRYPTION_KEY` protects the reversible Subsonic-compat credential and
  signs nothing else sensitive — rotate it by re-running the admin bootstrap
  only if you're comfortable invalidating every user's legacy-client access.
- MongoDB is not exposed outside the Docker network by default; keep it that
  way unless you have a specific reason and firewall/auth in place.
