"""Filesystem traversal: metadata extraction, artwork caching, deletion reconciliation."""

from __future__ import annotations

import logging
import os

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import get_settings
from app.repositories import catalog as catalog_repo
from app.repositories import scan_jobs as scan_jobs_repo
from app.worker.artwork import save_album_cover
from app.worker.tags import ExtractedTags, extract_tags, find_sidecar_artwork, is_supported

logger = logging.getLogger("dtp_tunes.worker.scanner")


def _cover_needs_refresh(album_doc: dict) -> bool:
    """True when the album has no cover path, or the cached file is missing."""
    relative = album_doc.get("coverArtPath")
    if not relative:
        return True
    settings = get_settings()
    absolute = os.path.join(settings.cache_path, relative)
    return not os.path.isfile(absolute)


def _iter_audio_files(music_root: str):
    for dirpath, _dirnames, filenames in os.walk(music_root):
        for filename in filenames:
            absolute = os.path.join(dirpath, filename)
            if not is_supported(absolute):
                continue
            real_root = os.path.realpath(music_root)
            real_path = os.path.realpath(absolute)
            if not real_path.startswith(real_root + os.sep):
                continue
            yield absolute


async def run_scan_job(db: AsyncIOMotorDatabase, job_id: str) -> None:
    settings = get_settings()
    music_root = settings.music_path

    if not os.path.isdir(music_root):
        logger.error("Music path %s does not exist", music_root)
        await scan_jobs_repo.complete_job(db, job_id, status="failed", last_error="Music path not found")
        return

    seen_paths: set[str] = set()

    try:
        for absolute_path in _iter_audio_files(music_root):
            relative_path = os.path.relpath(absolute_path, music_root)
            try:
                await _scan_one_file(db, absolute_path=absolute_path, relative_path=relative_path, job_id=job_id)
                seen_paths.add(relative_path)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to scan %s: %s", relative_path, exc)
                await scan_jobs_repo.update_progress(db, job_id, errorCount=1)
            await scan_jobs_repo.renew_lease(db, job_id, owner=os.environ.get("HOSTNAME", "worker"))

        existing_paths = await catalog_repo.all_song_paths(db)
        missing_paths = list(existing_paths - seen_paths)
        deleted_songs = await catalog_repo.delete_songs_by_paths(db, missing_paths)
        affected_albums = {s["albumId"] for s in deleted_songs if s.get("albumId")}
        for album_id in affected_albums:
            await catalog_repo.recount_album_songs(db, album_id)
        await catalog_repo.delete_orphan_albums(db)
        await catalog_repo.delete_orphan_artists(db)
        await catalog_repo.recount_genres(db)

        if missing_paths:
            await scan_jobs_repo.update_progress(db, job_id, removedCount=len(missing_paths))

        await scan_jobs_repo.complete_job(db, job_id, status="completed")
        logger.info("Scan job %s completed", job_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Scan job %s failed", job_id)
        await scan_jobs_repo.complete_job(db, job_id, status="failed", last_error=str(exc))


async def _scan_one_file(
    db: AsyncIOMotorDatabase,
    *,
    absolute_path: str,
    relative_path: str,
    job_id: str,
) -> None:
    stat = os.stat(absolute_path)

    existing = await db.songs.find_one({"path": relative_path}, {"fileMtime": 1, "fileSize": 1, "albumId": 1})
    if existing and existing.get("fileMtime") == int(stat.st_mtime) and existing.get("fileSize") == stat.st_size:
        # File unchanged — still refresh cover if the cached JPEG went missing.
        album_id = existing.get("albumId")
        if album_id:
            album_doc = await catalog_repo.get_album(db, album_id)
            if album_doc and _cover_needs_refresh(album_doc):
                tags = extract_tags(absolute_path)
                if tags:
                    artwork_bytes = tags.embedded_artwork or find_sidecar_artwork(os.path.dirname(absolute_path))
                    if artwork_bytes:
                        cover_path = save_album_cover(album_doc["_id"], artwork_bytes)
                        if cover_path:
                            await catalog_repo.set_album_cover_path(db, album_doc["_id"], cover_path)
        await scan_jobs_repo.update_progress(db, job_id, scannedCount=1)
        return

    tags: ExtractedTags | None = extract_tags(absolute_path)
    if tags is None:
        await scan_jobs_repo.update_progress(db, job_id, scannedCount=1, errorCount=1)
        return

    artist_doc = None
    if tags.album_artist:
        artist_doc = await catalog_repo.upsert_artist(db, name=tags.album_artist)

    album_doc = None
    if tags.album:
        album_doc = await catalog_repo.upsert_album(
            db,
            name=tags.album,
            artist_id=artist_doc["_id"] if artist_doc else None,
            artist_name=tags.album_artist,
            year=tags.year,
            genre=tags.genre,
        )

    if tags.genre:
        await catalog_repo.upsert_genre(db, tags.genre)

    if album_doc and _cover_needs_refresh(album_doc):
        artwork_bytes = tags.embedded_artwork or find_sidecar_artwork(os.path.dirname(absolute_path))
        if artwork_bytes:
            cover_path = save_album_cover(album_doc["_id"], artwork_bytes)
            if cover_path:
                await catalog_repo.set_album_cover_path(db, album_doc["_id"], cover_path)
                album_doc["coverArtPath"] = cover_path

    from app.repositories.base import normalize

    fields = {
        "title": tags.title,
        "normalizedTitle": normalize(tags.title),
        "albumId": album_doc["_id"] if album_doc else None,
        "albumName": tags.album,
        "artistId": artist_doc["_id"] if artist_doc else None,
        "artistName": tags.artist or tags.album_artist,
        "genre": tags.genre,
        "track": tags.track,
        "discNumber": tags.disc_number,
        "year": tags.year,
        "duration": tags.duration,
        "bitrate": tags.bitrate,
        "suffix": tags.suffix,
        "contentType": tags.content_type,
        "size": tags.size,
        "fileMtime": int(stat.st_mtime),
        "fileSize": stat.st_size,
    }
    _, created = await catalog_repo.upsert_song_by_path(db, path=relative_path, fields=fields)

    if album_doc:
        await catalog_repo.recount_album_songs(db, album_doc["_id"])

    await scan_jobs_repo.update_progress(db, job_id, scannedCount=1, **({"addedCount": 1} if created else {"updatedCount": 1}))
