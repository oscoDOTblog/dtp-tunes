# Two-Panel Add Music Flow

## Summary

Update the admin `/add-music` experience to begin with two prominent choices:

- **Upload with Link** — download from a supported URL.
- **Upload with Files** — choose local audio files.

Keep all existing ingest APIs, downloading, review, queue, and save behavior unchanged.

## Implementation Changes

- Replace the initial URL form on `/add-music` with two large, responsive, fully clickable option panels describing each method.
- When **Upload with Link** is selected:
  - Show only the URL input, **Load details** button, errors, and a **Back to upload options** action.
  - Reveal the existing album setup fields only after metadata loads successfully.
  - Hide/reset loaded metadata if the URL is edited afterward, preventing details from a previous link from being submitted.
  - Preserve the existing cover selection, **Download & review tracks**, background queue, and post-download review flow.
- When **Upload with Files** is selected, navigate to the existing `/add-music/upload` page.
- Simplify the file picker:
  - Make the complete dashed upload area clickable.
  - Add a prominent **Choose audio files** button-style label.
  - Move supported formats into short secondary copy.
  - Retain multiple-file selection and the existing album, cover, track ordering, progress, and submission workflow.
  - Rename the existing return action to **Back to upload options**.
- Preserve admin-only access and responsive/mobile behavior.

## Interfaces

- No backend endpoints, request payloads, routes, or shared types change.
- Add only local UI state for the selected link mode and whether metadata has been successfully loaded.

## Test Plan

- Run the web app’s typecheck and lint commands.
- Verify `/add-music` initially displays exactly two prominent options and no URL or album form.
- Verify link selection initially shows only the URL controls.
- Verify successful metadata retrieval reveals populated album setup fields.
- Verify failed retrieval leaves album setup hidden and displays the error.
- Verify editing the URL after retrieval hides stale album details until details are loaded again.
- Verify both one-off download and background queue submissions continue into their existing flows.
- Verify the file option opens `/add-music/upload`, the entire picker area opens the native file chooser, and selecting files reveals the unchanged review/upload workflow.
- Verify both flows provide a clear path back to the two-panel chooser and remain usable on narrow screens.

## Assumptions

- The chooser is restored through explicit back links rather than persistent tabs.
- The selected file-upload copy is **Choose audio files**.
- “After downloading, resume the rest of the UX flow” means retaining the current job review and queue behavior without consolidating those pages.
