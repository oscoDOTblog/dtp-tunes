---
name: Song row playlist menu
overview: Add a Spotify-style song kebab menu and a complete save-to-playlist picker with creation, recent ranking, cover mosaics, duplicate prevention, and toast feedback.
todos:
  - id: menu-primitive
    content: Add Menu dropdown primitive in components/ui/Menu.tsx (outside-click + Escape close)
    status: completed
  - id: playlist-picker-api
    content: Enrich playlist list responses with coverArtIds and containsSong, with recent sorting for the picker
    status: completed
  - id: toast-system
    content: Add a global toast provider and use it for playlist add/remove/error feedback
    status: completed
  - id: save-dialog
    content: Add SaveToPlaylistDialog with recent playlists, cover mosaics, duplicate-disabled rows, and create-plus-add
    status: completed
  - id: songrow-kebab
    content: Swap duration for kebab menu on hover in SongRow and wire up the dialog
    status: completed
  - id: playlist-covers
    content: Add reusable playlist cover mosaics to the picker, sidebar items, and playlist detail
    status: completed
  - id: removal-feedback
    content: Add toast feedback to existing playlist song removal
    status: completed
  - id: verify
    content: Run API tests, web typecheck/lint, and verify menu, picker, duplicate, creation, artwork, and toast flows
    status: completed
isProject: false
---

# Song Row Kebab Menu + Save to Playlist

## Context

The backend already supports the core mutations:
- `PATCH /api/playlists/{id}` with `songIdsToAdd: [songId]` appends a song
- `POST /api/playlists` accepts both a name and initial `songIds`, enabling create-and-add in one request

The song row ([web/src/components/music/SongRow.tsx](web/src/components/music/SongRow.tsx)) already renders a decorative `MoreHorizontal` icon next to the duration; it just isn't interactive.

## Changes

### 1. New `components/ui/Menu.tsx` — small dropdown primitive
No UI library exists in this app (custom components only), so add a lightweight anchored dropdown: trigger + absolutely-positioned panel, closes on outside click / Escape, `role="menu"` items. Reusable for future row actions (add to queue, go to album, etc.).

### 2. Playlist-picker API enrichment
Update [api/app/routes/api_playlists.py](api/app/routes/api_playlists.py), [api/app/repositories/playlists.py](api/app/repositories/playlists.py), and the playlist models/types so `GET /api/playlists` can accept picker-specific query parameters:
- `sort=recent` orders by `updatedAt` descending without changing the existing alphabetical sidebar order
- `songId=<id>` returns `containsSong` for duplicate detection
- Each playlist returns up to four unique `coverArtIds`, resolved with one batched song lookup across all listed playlists (not one query per playlist)

The mutation endpoint must also reject duplicate additions server-side, so a stale picker or concurrent click cannot create duplicates.

### 3. Global toast feedback
Add `components/ui/ToastProvider.tsx` and mount it from [web/src/app/(main)/layout.tsx](web/src/app/(main)/layout.tsx). Provide a small `useToast()` API for success, informational, and error messages with timed dismissal and an accessible live region. Use it for:
- Added to playlist
- Playlist created and song added
- Song removed from playlist
- Already in playlist / API failures

### 4. New `components/music/PlaylistCover.tsx`
Render a reusable square mosaic from up to four `coverArtIds`; use the existing `coverUrl` helper and fall back to a themed music/list icon when empty. Use it in the picker, existing sidebar `PlaylistListItem`, and playlist detail header.

### 5. New `components/music/SaveToPlaylistDialog.tsx`
Modal overlay (same fixed-overlay pattern as `NowPlayingSheet`) that:
- Fetches `/api/playlists?sort=recent&songId=<song.id>`
- Lists recent playlists first with mosaic art, name, and song count in a scrollable responsive panel
- Disables playlists where `containsSong` is true and labels them “Already added”
- On an enabled row: `api.patch("/api/playlists/{id}", { songIdsToAdd: [song.id] })`, shows a success toast, then closes
- Includes a “New playlist” action that reveals a name input; submitting calls `POST /api/playlists` with `songIds: [song.id]`, then confirms by toast and closes
- Empty state when the user has no playlists yet

### 6. Update `SongRow.tsx`
- Duration + kebab share the last grid cell: duration visible normally, hidden on `group-hover`; kebab button (`MoreHorizontal`) shown on hover in its place (Spotify behavior)
- Kebab opens the `Menu` with one item for now: "Save to playlist" → opens `SaveToPlaylistDialog`
- On mobile (no hover), the kebab is always visible in place of nothing being tappable today

### 7. Existing playlist page integration
- Replace the current plain playlist heading with `PlaylistCover`
- Keep existing remove behavior, but show success/error toasts
- Refresh data after mutations so song counts, duration, and cover mosaic stay current

## Still not in scope

- More kebab items: Play next / Add to queue, Go to album / artist, Star, Remove from this playlist (when rendered inside a playlist page)
- Reordering songs within a playlist (backend `replace_songs` supports it; UI needs drag-and-drop or move up/down)
- Manually uploading custom playlist cover artwork
- Pinning playlists or keeping a separate per-user `lastUsedAt`; V1 “Recent” uses the existing `updatedAt`
