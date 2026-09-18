# Raw Lyrics and Lyrics Editor for dtp-tunes

## Summary

Add unsynchronized lyrics backed by UTF-8 `.txt` sidecars, plus an admin-only editor accessible from each song’s menu.

For `01 - Song.flac`, the durable lyrics file will be `01 - Song.txt`. Admins can paste lyrics or load a `.txt` file into a large textarea, review it, and explicitly save. Line breaks are preserved. Timestamps are not required.

## Implementation Changes

- Extend library scanning to import same-basename `.txt` sidecars into each MongoDB song document.
- Track sidecar modification metadata separately so edits and deletions are detected even when the audio file is unchanged.
- Make only the API container’s `/music` mount writable; keep the worker mount read-only.
- Add authenticated web endpoints:
  - `GET /api/songs/{id}/lyrics` for all signed-in users.
  - `PUT /api/songs/{id}/lyrics` for admins, accepting raw text and atomically writing the `.txt` sidecar before updating MongoDB.
  - `DELETE /api/songs/{id}/lyrics` for admins, removing the sidecar and clearing MongoDB.
- Reject unknown songs, paths outside the music root, non-UTF-8 uploads, and lyrics larger than 1 MiB. Filesystem failures return a clear error without claiming the lyrics were saved.
- Add an admin-only “Edit lyrics” action to `SongRow`.
- Add a lyrics dialog containing:
  - Song title and artist.
  - Large multiline textarea using a whitespace-preserving font/layout.
  - `.txt` file picker that reads the file locally into the textarea.
  - Save, delete, and cancel controls.
  - Unsaved-change confirmation when closing or replacing edited text with an uploaded file.
  - Loading, saving, empty, and error states.
- Save pasted and uploaded content through the same JSON API; multipart server upload is unnecessary because the selected text file is previewed before saving.

## Subsonic Compatibility

- Implement classic `getLyrics`, returning the complete raw text.
- Implement [`getLyricsBySongId`](https://opensubsonic.netlify.app/docs/endpoints/getlyricsbysongid/) with `synced: false`, `lang: "und"`, and one untimed entry per text line.
- Advertise `songLyrics` version 1 through `getOpenSubsonicExtensions`.
- Ensure JSON and XML correctly serialize raw lyric bodies and structured line text.
- Existing songs without lyrics return a successful empty result; unknown song IDs return Subsonic error `70`.

## Test Plan

- Import, update, and remove a sidecar while the audio file remains unchanged.
- Preserve Unicode, blank lines, paragraph breaks, and final text through paste, file selection, API storage, and retrieval.
- Verify atomic writes and safe path containment.
- Verify ordinary users can read but cannot create, edit, or delete lyrics.
- Test missing songs, invalid UTF-8 files, oversized content, read-only/permission failures, and sidecar deletion.
- Test the editor’s load, file preview, save, delete, unsaved-change warning, and error states.
- Validate `getLyrics`, `getLyricsBySongId`, and extension discovery in JSON and XML.

## Assumptions

- Sidecars use the audio file’s exact stem with a lowercase `.txt` extension.
- UTF-8 and UTF-8 with BOM are accepted.
- Newline style may be normalized to `\n`, while the visible line and paragraph structure is preserved.
- The sidecar is authoritative and MongoDB remains a reconstructable scan cache.
- Embedded tags, `.lrc`, timestamps, language selection, and multiple lyric versions remain outside v1.
