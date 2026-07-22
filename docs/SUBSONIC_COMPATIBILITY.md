# OpenSubsonic compatibility

dtp-tunes implements a practical subset of the
[OpenSubsonic API](https://opensubsonic.netlify.app/docs/api-reference/)
(itself a documented superset of the original Subsonic API) under `/rest`.
This document is the source of truth for what's implemented, how auth works,
and which endpoint families are intentionally out of scope for V1 (see also
[`docs/V1_SCOPE.md`](V1_SCOPE.md)).

Every endpoint is registered for both the bare and `.view`-suffixed path
(e.g. `/rest/ping` and `/rest/ping.view`), accepts GET query parameters or
`application/x-www-form-urlencoded` POST bodies, and returns JSON by default
or XML when `f=xml` is supplied (`api/app/services/subsonic_format.py`).

## Authentication

Implemented, in priority order (`api/app/services/auth_service.py`):

1. **API key** — `apiKey=<keyId>.<secret>` query param or `X-Api-Key`
   header. Keys are created per-user in **Settings → Subsonic API keys**,
   stored as `{keyId}.{secret}` where only an Argon2id hash of `secret` is
   persisted. This is the OpenSubsonic `apiKeyAuthentication` extension and
   the **recommended** auth mode for any client that supports it.
2. **Token/salt** (`u`, `t`, `s`) — `t = MD5(subsonicSecret + s)`, matching
   the original Subsonic scheme, but computed against a per-user
   **Subsonic compatibility secret** instead of the web password (see
   "Why a separate compatibility secret?" below).
3. **Legacy password** (`u`, `p`) — plaintext or `enc:<hex>`-encoded,
   compared directly against the same compatibility secret.

### Why a separate compatibility secret?

Web passwords are hashed with Argon2id and are never recoverable — by
design, the server cannot reconstruct them to answer a Subsonic
token/salt or legacy-password challenge, both of which require comparing
against (or deriving from) the *original* credential.

Every user is therefore also issued a random, high-entropy
**Subsonic compatibility secret**, unrelated to their web password, and
stored reversibly using AES-256-GCM under `APP_ENCRYPTION_KEY`
(`api/app/security.py`). This is a deliberate, documented security
tradeoff: it lets legacy Subsonic clients work at all, while keeping the
web login path fully one-way. If `APP_ENCRYPTION_KEY` is ever compromised,
rotate it and every user's Subsonic secret is invalidated (users keep their
web password); their Subsonic clients will need reconfiguring.

**Recommendation:** prefer API keys or a strong random `ADMIN_PASSWORD`
plus per-user accounts, and put dtp-tunes behind HTTPS if it's reachable
outside a trusted LAN — token/salt still exposes the compatibility secret
to offline brute force if intercepted, and legacy password mode sends it
close to directly.

In the web UI, **Settings → Subsonic client password** lets you reveal or
rotate your compatibility secret. Use your web username plus that password
in classic Subsonic clients. Clients that support OpenSubsonic API keys
should use **Settings → Subsonic API keys** instead.

## Endpoint coverage

### System

| Endpoint | Status | Notes |
| --- | --- | --- |
| `ping` | ✅ Tested | |
| `getLicense` | ✅ Tested | Always reports a valid, unlimited license (self-hosted, no licensing gate) |
| `getOpenSubsonicExtensions` | ✅ Tested | Advertises `transcodeOffset`, `formPost`, `apiKeyAuthentication` |

### Browse — folder-style

| Endpoint | Status | Notes |
| --- | --- | --- |
| `getMusicFolders` | ✅ Tested | Single folder (`MUSIC_FOLDER_ID`/`MUSIC_FOLDER_NAME`) |
| `getIndexes` | ✅ Tested | Artist-name-first-letter buckets |
| `getMusicDirectory` | ✅ Tested | Accepts an artist id (lists albums) or album id (lists songs) |

### Browse — ID3-tagged

| Endpoint | Status | Notes |
| --- | --- | --- |
| `getArtists` | ✅ Tested | |
| `getArtist` | ✅ Tested | |
| `getAlbum` | ✅ Tested | |
| `getSong` | ✅ Tested | |
| `getGenres` | ✅ Tested | |
| `getAlbumList2` | ✅ Tested | `random`, `newest`, `byGenre`, `byYear`, alphabetical |
| `getRandomSongs` | ✅ Tested | Optional `genre` filter |
| `getSongsByGenre` | ✅ Tested | |
| `search3` | ✅ Tested | Case-insensitive substring match across artists/albums/songs |
| `getStarred2` | ✅ Tested | |

### User state

| Endpoint | Status | Notes |
| --- | --- | --- |
| `star` / `unstar` | ✅ Tested | Accepts repeated `id`, `albumId`, `artistId` |
| `scrobble` | ✅ Tested | `submission=true` records play history + increments `playCount` |
| `getPlayQueue` / `savePlayQueue` | ✅ Tested | Shared with the web player's `/api/queue` |
| `getPlaylists` / `getPlaylist` | ✅ Tested | |
| `createPlaylist` / `updatePlaylist` / `deletePlaylist` | ✅ Tested | |
| `getUser` | ✅ Tested | Reports `adminRole` from the account's role |
| `getScanStatus` / `startScan` | ✅ Tested | `startScan` requires the admin role |

### Media

| Endpoint | Status | Notes |
| --- | --- | --- |
| `stream` | ✅ Tested | Byte-range aware; `format=mp3\|opus` triggers bounded live transcoding |
| `download` | ✅ Tested | Always serves the original file, range-aware |
| `getCoverArt` | ✅ Tested | Resizes cached album art via `size=` |

### Explicitly not implemented (V1)

Podcasts, video/movies, chat, sharing/public links, internet radio, and
jukebox mode. See [`docs/V1_SCOPE.md`](V1_SCOPE.md) for the rationale.

## Response shape

- JSON envelope: `{"subsonic-response": {"status": "ok", "version": "...", "type": "dtp-tunes", "serverVersion": "...", "openSubsonic": true, ...}}`.
- XML envelope: equivalent structure rendered by
  `services/subsonic_format.render_envelope`, with list-valued fields
  expanded into repeated child elements.
- Errors follow the standard Subsonic error codes (`0` generic, `10` missing
  parameter, `40` wrong credentials, `50` not authorized, `70` not found —
  see `SubsonicError` in `services/subsonic_format.py`).

## Tested client matrix

This matrix reflects **protocol-level contract tests** in `api/tests`
(`test_subsonic_envelopes.py`, `test_subsonic_auth.py`) plus manual
verification against the endpoints above. It is not a substitute for
testing against real client apps before depending on this for daily use.

| Client family | Expected compatibility |
| --- | --- |
| DSub / Subtracks-style Android clients | Core browse/search/star/playlists/stream should work via token/salt or API key |
| Substreamer / play:Sub (iOS) | Same baseline; verify `getOpenSubsonicExtensions` handling for API-key auth |
| Symfonium, Amperfy | ID3 browse + `getAlbumList2` + play queue sync should work |
| Airsonic/Navidrome-targeted integrations | Any client only using the endpoints above should be compatible; anything touching podcasts/jukebox/sharing will not be |

If you validate a specific client against a real deployment, please note
the client name/version and which endpoints it exercised here.
