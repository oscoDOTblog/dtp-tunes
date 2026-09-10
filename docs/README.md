# Android Subsonic download troubleshooting

Use this guide when an Android Subsonic client reports no download progress for
songs, albums, or playlists. Start by checking the running deployment, then
follow one track through the API and gateway logs.

## Which containers to inspect

Downloads follow this path:

```text
Android client → Runtipi Traefik → gateway → api → /music
```

| Service | What to check |
| --- | --- |
| `api` | Authentication, media paths, permissions, transcoding, bytes delivered |
| `gateway` | Requests reaching dtp-tunes, HTTP status, bytes sent, proxy failures |
| Runtipi Traefik | Routing and TLS when requests do not reach the gateway |
| `worker` | Library scans or stale catalog paths; it does not serve downloads |
| `web` | Not involved in Subsonic audio transfers |

Container names commonly look like `dtp-tunes-api-1` and
`dtp-tunes-gateway-1`, but depend on the Compose project name.

## Verify the deployment first

On the Docker host, list containers and inspect the Compose labels:

```sh
docker ps --format '{{.Names}}\t{{.Image}}'
docker inspect <api-container-name> <gateway-container-name> \
  --format '{{.Name}} → project={{index .Config.Labels "com.docker.compose.project"}} directory={{index .Config.Labels "com.docker.compose.project.working_dir"}} files={{index .Config.Labels "com.docker.compose.project.config_files"}}'
```

Use the directory, project name, and Compose files shown by these labels.
Building another checkout or project will not update the containers receiving
your phone's requests. If the existing project uses an explicit project name,
include the same `-p <project-name>` in subsequent Compose commands.

For the standard Runtipi deployment, after updating that checkout:

```sh
docker compose -f docker-compose.yml -f docker-compose.runtipi.yml up -d --build api gateway
docker compose -f docker-compose.yml -f docker-compose.runtipi.yml logs --since=10m -f api gateway
```

For a local deployment, omit the Runtipi overlay. Keep the same Compose file
selection and project name for deployment and log commands.

The updated API emits `dtp_tunes.transfer` records with `request_started` and
`request_finished`. The gateway emits JSON records containing `bytes_sent` and
`request_id`. Older plain-text access logs with full query strings indicate
that these logging changes are not active in that container, or that you are
reading historical logs. Check timestamps after recreation.

## Reproduce with one song

1. Start following `api` and `gateway` logs.
2. Download one song and note the time and client quality setting.
3. Match API and gateway entries using `request_id`.
4. Compare an original/raw download with an MP3 download if progress is unclear.

An offline download can use `/rest/stream.view`; it does not have to use
`/rest/download.view`. In the observed Substreamer requests, `format=raw`
served original audio and `format=mp3` requested live FFmpeg transcoding.
Clients fetch individual tracks when downloading an album or playlist.

## What the successful retry showed

On September 10, 2026, Substreamer requested a track with `format=mp3` and no
Range header. The matching logs reported:

| Field | API | Gateway |
| --- | --- | --- |
| HTTP status | `200` | `200` |
| Bytes sent | `11489425` | `11563136` |
| Duration | `19247.6 ms` | `19.246 s` |
| Content type | `audio/mpeg` | — |
| Expected bytes | `None` | — |
| Response complete | `True` | — |

The API finished sending about 11.49 MB of audio, and the gateway also sent
data downstream without a reported HTTP error. The slightly larger gateway
count is consistent with HTTP chunked-transfer framing; the two byte counters
measure different layers.

`expected_bytes=None` means there was no `Content-Length` response header.
The current live-transcoding implementation does not provide one, even when
the client sends `estimateContentLength=true`. This may prevent a client from
displaying useful download progress. Original/raw file responses provide a
length, making them a useful comparison. This is a plausible explanation for
the earlier display, not a confirmed diagnosis of the original failure.

`complete=True` means the API finished its response. It does not verify that
Android saved the file, or independently verify that FFmpeg produced the
entire expected track. If the saved audio is truncated, investigate FFmpeg
and compare the downloaded track's duration with the original.

## Interpret failures

| Observation | Next step |
| --- | --- |
| No matching gateway request | Check client URL, network, DNS/TLS, and Traefik routing |
| Gateway `502` or `504` | Check API availability and upstream connectivity/timeouts |
| `auth_failed` | Use the Subsonic client password or supported API key from Settings |
| HTTP `200` with JSON/XML on a media request | Inspect for a Subsonic error envelope; this is not audio |
| `media_missing` | Refresh the client's catalog; the song ID was not found |
| `media_file_missing` | Check the API's `/music` mount and stored catalog path |
| `media_open_failed` | Check file and directory permissions for the container's UID/GID |
| `206 Partial Content` | Normally a range request for seeking or resuming, not an error |
| `416` | Check the requested range and clear the track's stale partial download |
| `complete=False` or `request_failed` | Investigate disconnects and file/stream failures |
| API sends audio but gateway fails or sends much less | Investigate the downstream proxy/client connection |
| Both send audio successfully but the app still fails | Check Android storage, app download settings, and device logs |

The troubleshooting changes also corrected suffix byte ranges (`bytes=-N`)
and added diagnostics for unreadable files before sending successful response
headers. The successful retries do not establish that the range fix caused
the recovery.

Before sharing older logs, redact query-string credentials such as `u`, `t`,
`s`, `p`, and `apiKey`. The new transfer/access diagnostics omit query strings;
upstream proxy logs may still include them.

See [Download debugging](DOWNLOAD_DEBUGGING.md) for mount checks and further
failure details, and [Subsonic compatibility](SUBSONIC_COMPATIBILITY.md) for
authentication and supported endpoints.
