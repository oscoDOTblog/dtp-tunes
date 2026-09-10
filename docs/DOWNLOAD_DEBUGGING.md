# Android / Subsonic download debugging

Traffic flows through Runtipi Traefik → dtp-tunes `gateway` → `api` →
read-only `/music` bind mount. `worker` scans files and populates MongoDB;
`web` does not serve Subsonic downloads. Albums/playlists are browsed through
Subsonic and their tracks fetched individually by the client.

## Deploy diagnostics

From the dtp-tunes directory on the Docker host, using the same .env and
Compose project as the existing deployment:

```sh
docker compose -f docker-compose.yml -f docker-compose.runtipi.yml up -d --build api gateway
docker compose -f docker-compose.yml -f docker-compose.runtipi.yml logs --since=10m -f api gateway
```

For local deployments omit `-f docker-compose.runtipi.yml` (and use the same
file selection consistently). Retry downloading just one song in the Android
app and note the time. No debug environment setting is needed.

API `request_started` / `request_finished` records cover all `/rest/` requests,
including `.view` and POST. Correlate by `request_id`, also returned as
`X-Request-ID` and recorded in gateway access logs. `media_requested` identifies
the song, client, requested format and Range. Credentials, full URLs, and form
bodies are excluded from these diagnostic logs. Uvicorn's default access log
is disabled in Compose because it includes credential-bearing query strings.
Older logs and upstream proxy error/access logs may still contain credentials;
redact them before sharing.

## Interpret a retry

- No gateway request: investigate Android app/server URL, DNS/TLS, and Runtipi
  Traefik. Find the proxy container with `docker ps --format '{{.Names}}\t{{.Image}}'`
  and inspect `docker logs --since=10m <container-name>`. Do not attach Runtipi
  forward-auth to this route; Subsonic apps cannot complete browser login.
- Gateway 502/504: API connectivity, availability, or upstream timeout.
- `auth_failed`: configure the app with the Settings → Subsonic client password
  (or supported API key), not the web login password. Subsonic error envelopes
  can have HTTP 200; JSON/XML content is not a successful audio download.
- `media_missing`: stale/unknown song ID; refresh the client's library.
- `media_file_missing`: database path no longer exists under the API's `/music`.
  Confirm MUSIC_HOST_PATH and mounts, then rescan if the library moved.
- `media_open_failed`: inspect error type/errno and permissions. API and worker
  must both read the same mount as PUID/PGID (default 1001:1001).
- 416: client requested a range outside the current file; clear that track's
  partial download and retry. Suffix ranges now correctly return the last N bytes.
- Audio response with `complete=False` or bytes below expected: interrupted
  transfer or file read failure. Look for `request_failed` with the same ID.
- API completes with expected bytes but gateway sends fewer: downstream
  disconnect/proxy issue. Gateway 499 also indicates a client disconnect.
- Both complete with audio bytes: investigate Android app storage/download
  settings and device logs. Server completion does not prove a file was saved.
- `format=mp3` or `opus` uses live FFmpeg in the API; inspect API errors and
  transcode overload (503). `/rest/download` serves the original file.

Inspect mount identity without printing .env secrets:

```sh
docker compose exec api id
docker compose exec worker id
docker compose exec api ls -ld /music
```

For a reported missing/unreadable path, use `docker compose exec api ls -l
'/music/path/from/the/log'`. Check directory traversal permissions as well as
file readability. Inspect `worker` logs only if catalog paths/scans are wrong;
MongoDB stores metadata and does not carry audio bytes.

These diagnostics measure bytes handed to the ASGI server and gateway client
connection, not confirmation of persistence on Android. The production cause
must be confirmed from a reproduction; the range fix alone does not establish
why a particular device failed.
