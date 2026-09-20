# Add Music deployment on `rath`

Tunes now has an admin-only Add Music UI for URL downloads, queued jobs, track review, and MP3 upload. The existing VideoDL deployment, queue, history, and URL remain unchanged. Tunes uses its own MongoDB `ingestJobs` collection and a persistent `ingest-data` Docker volume; never delete that volume during routine recreation. Sources requiring cookies are not supported in this phase.

## Preflight and permissions

Run these commands on `rath` from `~/apps/dtp/dtp-tunes`. Confirm the library path and account first; these examples assume `/mnt/yuna/navidrome/music` and `yui` (`1000:1003`). The local Mac's `501:20` is not appropriate on `rath`.

```sh
id yui
grep -E '^(PUID|PGID|MUSIC_HOST_PATH)=' .env
stat -c '%A %u:%g %n' /mnt/yuna/navidrome/music
```

Set `PUID=1000`, `PGID=1003`, and `MUSIC_HOST_PATH=/mnt/yuna/navidrome/music` in the server's `.env`. Keep its other secrets and settings intact. Install the host ACL tools if `setfacl` is absent. Apply access ACLs to existing *directories only*, not audio files; then default ACLs so newly created directories inherit access. These commands do not change ownership or grant world write access:

```sh
sudo find /mnt/yuna/navidrome/music -type d -exec setfacl -m u:yui:rwx,d:u:yui:rwx {} +
getfacl -p /mnt/yuna/navidrome/music
getfacl -p '/mnt/yuna/navidrome/music/Kzyboost/36 by 37'
```

The `find` can take time on a large library. Check its exit status and rerun if interrupted. VideoDL's current save path creates an artist directory, creates a staging directory *inside that artist*, then renames staging to the final album name. The staging directory should therefore inherit the artist directory's default ACL, and the rename retains it. Verify both paths on `rath`: have VideoDL create a disposable album through its normal save workflow, inspect `getfacl` on the resulting artist and album, and verify `yui` can create a temporary file inside it. If the ACL is absent after promotion, reapply the directory-only ACL command and investigate the host filesystem's ACL inheritance. VideoDL currently replaces an existing album directory during its own save; that behavior is unchanged by this Tunes release, so avoid using VideoDL to overwrite an album with sidecar lyrics you need to preserve.

To test an existing root-owned album without altering its songs:

```sh
sudo -u yui test -w '/mnt/yuna/navidrome/music/Kzyboost/36 by 37'
sudo -u yui touch '/mnt/yuna/navidrome/music/Kzyboost/36 by 37/.tunes-permission-probe'
sudo -u yui rm '/mnt/yuna/navidrome/music/Kzyboost/36 by 37/.tunes-permission-probe'
```

## Recreate and verify

Validate configuration before recreation, then rebuild. The `ingest-init` one-shot service prepares only the named staging volume. It does not modify the host music tree. The API and ingestion worker bind `/music` read-write; the scanner worker binds it read-only.

```sh
docker compose -f docker-compose.yml -f docker-compose.runtipi.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose.runtipi.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.runtipi.yml exec api id
docker compose -f docker-compose.yml -f docker-compose.runtipi.yml exec ingest-worker id
docker compose -f docker-compose.yml -f docker-compose.runtipi.yml exec api stat -c '%A %u:%g %n' /music
docker compose -f docker-compose.yml -f docker-compose.runtipi.yml ps
```

In the admin UI, upload a small disposable MP3 to a test album, confirm it appears after the scan, add a `.txt` lyric sidecar through Edit song lyrics, and test one URL download through review/save. Confirm a queued download completes and that cancel/retry works. Check that ordinary users cannot open Add Music or its APIs. Check the already-running VideoDL UI and its existing queue/history afterward. A scan enqueue failure is reported separately from a successful file save; retry a library scan from Settings if needed.

## Rollback

Redeploy the previous Tunes image/revision using the same Compose command, leaving VideoDL and its data untouched. Keep `ingest-data` and MongoDB intact for investigation; do not run `docker compose down -v`. If you need to remove the `yui` directory ACLs later, first ensure Tunes no longer needs uploads or lyric writes, then remove only the named ACL entries (`u:yui` and `d:u:yui`) from directories after reviewing `getfacl`. Do not remove ACLs that predated this deployment.
