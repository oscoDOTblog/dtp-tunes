# Apple Music → YouTube Music Playlist Import

## Summary

Add an admin-only playlist transfer workflow:

1. Choose Apple Music as the source and YouTube Music as the destination.
2. Paste a public Apple Music playlist URL.
3. Extract its metadata and tracks through the Apple Music API.
4. Match each track to YouTube videos in a background job.
5. Review proposed matches, replace or skip individual results, and select or create a destination playlist.
6. Confirm the import, preserving source order and skipping videos already in the destination.

Use the official APIs. YouTube writes require a one-time OAuth grant even when developer credentials come from Docker environment variables; store the resulting refresh token encrypted. [Apple Music API](https://developer.apple.com/documentation/applemusicapi), [YouTube playlist insertion](https://developers.google.com/youtube/v3/docs/playlistItems/insert), [Google offline OAuth](https://developers.google.com/identity/protocols/oauth2/web-server).

## Implementation Changes

- Add a dedicated `/import-playlist` admin page and navigation item, separate from “Add Music,” since this feature transfers external playlist metadata rather than downloading music into dtp-tunes.
- Provide a staged UI:
  - source platform selector with Apple Music enabled;
  - public playlist URL input and extraction progress;
  - review table showing title, artist, album, duration, selected YouTube result, confidence, and status;
  - per-track YouTube search/replacement and skip controls;
  - destination selector listing owned YouTube playlists plus “Create new,” defaulting to a new private playlist using the Apple playlist name;
  - import progress and final counts for added, duplicate, skipped, unmatched, and failed tracks.
- Add admin-protected `/api/playlist-transfers/*` endpoints for:
  - configuration/connection status;
  - Google OAuth start, callback, and disconnect;
  - destination playlist listing;
  - transfer creation/status;
  - manual candidate search and match replacement;
  - confirmation and import execution.
- Validate Apple URLs strictly, extract storefront and playlist ID, paginate all playlist tracks, and return a clear unsupported error when a URL is not accessible as a public catalog playlist.
- Generate Apple developer JWTs server-side from Docker configuration. Add documented environment settings for Apple team ID, key ID, private key, and default storefront.
- Add Google OAuth client ID/secret settings and derive the redirect URL from `APP_PUBLIC_URL`. Request offline access with the minimum YouTube scope that supports playlist reads and writes; encrypt the refresh token with the existing application encryption key.
- Add a dedicated playlist-transfer worker service. Jobs have explicit `extracting`, `readyForReview`, `importing`, `completed`, and `failed` states and remain recoverable across API/container restarts.
- Store transfer documents in MongoDB containing ownership, source metadata, ordered source tracks, proposed and user-selected matches, progress counters, destination details, timestamps, and sanitized errors. Never expose OAuth tokens or private keys through API responses.
- Match tracks by searching up to five YouTube candidates, fetching candidate durations in batches, and scoring normalized title/artist agreement, duration proximity, official/Topic signals, and penalties for covers, live versions, karaoke, reactions, sped-up/slowed, remixes, and compilations. Low-confidence results remain unmatched until replaced or skipped.
- Before importing, paginate the destination playlist’s video IDs. Insert selected nonduplicates in Apple source order, continue past per-track failures, persist progress after every item, and make confirmation retry-safe.
- Surface quota/auth failures clearly. Preserve the review job when credentials expire or quota is exhausted so the admin can reconnect or retry without repeating accepted matches.

## Public Interfaces and Configuration

- New response types: integration status, transfer summary/detail, source track, YouTube candidate, selected match, destination playlist, and import result.
- New Docker environment variables:
  - `APPLE_MUSIC_TEAM_ID`
  - `APPLE_MUSIC_KEY_ID`
  - `APPLE_MUSIC_PRIVATE_KEY`
  - `APPLE_MUSIC_DEFAULT_STOREFRONT=us`
  - `GOOGLE_OAUTH_CLIENT_ID`
  - `GOOGLE_OAUTH_CLIENT_SECRET`
- New MongoDB collections/indexes for the singleton admin YouTube connection, OAuth state with TTL, and playlist-transfer jobs indexed by status and creation time.
- Update `.env.example`, Compose services, architecture documentation, and setup instructions, including the exact Google redirect URI and YouTube Data API enablement.

## Test Plan

- Unit-test Apple URL validation, pagination, JWT construction, response normalization, candidate scoring, exclusion penalties, confidence thresholds, ordering, and duplicate detection.
- API-test admin authorization, missing configuration, OAuth state validation, encrypted token persistence, job state transitions, manual replacement/skipping, confirmation validation, and sanitized failures.
- Worker-test extraction, matching, refresh-token renewal, destination creation/selection, multi-page duplicate loading, ordered insertion, partial failures, quota errors, restart recovery, and idempotent retries with mocked Apple/Google APIs.
- Frontend-test the complete staged flow, loading/error/empty states, connection handling, review edits, destination selection, confirmation, polling, and final summary.
- Run backend lint/tests and frontend lint, typecheck, and production build.

## Assumptions

- Version one supports public Apple Music playlist URLs accessible with an Apple developer token; Apple personal-library playlists requiring a Music User Token are out of scope.
- One dtp-tunes admin connects one Google/YouTube account. Other users cannot view or run transfers.
- “YouTube Music playlist” is implemented as an ordinary YouTube playlist through the official YouTube Data API, which is available in YouTube Music when its videos are music-compatible.
- Imports never modify the Apple source or the dtp-tunes local library.
- Existing destination contents are preserved, and matching video IDs already present are skipped.
- Newly created destination playlists are private by default.
s