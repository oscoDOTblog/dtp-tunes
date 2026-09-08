"""JSON-API-side media endpoints for the Next.js frontend (cookie-authenticated)."""

from __future__ import annotations

import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.deps import get_db, require_user
from app.repositories import catalog as catalog_repo
from app.services.cover_art import render_cover_art
from app.services.media import (
    build_album_zip,
    content_type_for,
    resolve_music_path,
    sanitize_download_filename,
    stream_file_with_range,
    track_filename,
    transcode_stream,
)

router = APIRouter(prefix="/api", tags=["media"])


@router.get("/stream/{song_id}")
async def stream_song(
    song_id: str,
    request: Request,
    format: str | None = Query(default=None),
    maxBitRate: int = Query(default=192),
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(require_user),
):
    song = await catalog_repo.get_song(db, song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    absolute_path = resolve_music_path(song["path"])
    if format and format != "raw":
        return await transcode_stream(absolute_path, format_=format, max_bitrate_kbps=maxBitRate)
    return await stream_file_with_range(request, absolute_path, content_type_for(song.get("suffix", "")))


@router.get("/download/{song_id}")
async def download_song(
    song_id: str,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(require_user),
):
    """Download the original file for one song (Content-Disposition: attachment)."""
    song = await catalog_repo.get_song(db, song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    absolute_path = resolve_music_path(song["path"])
    suffix = song.get("suffix", "")
    filename = f"{sanitize_download_filename(song.get('title') or 'track', 'track')}"
    if suffix:
        filename += f".{suffix.lower()}"
    return await stream_file_with_range(
        request, absolute_path, content_type_for(suffix), download_filename=filename
    )


@router.get("/albums/{album_id}/download")
async def download_album(
    album_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(require_user),
):
    """Download a whole album as a zip of its original track files."""
    album = await catalog_repo.get_album(db, album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    songs = await catalog_repo.list_songs_by_album(db, album_id)
    if not songs:
        raise HTTPException(status_code=404, detail="Album has no downloadable tracks")
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()
    for song in songs:
        try:
            absolute_path = resolve_music_path(song["path"])
        except HTTPException:
            continue
        entries.append(
            (absolute_path, track_filename(song.get("title") or "Unknown Track", song.get("track"), song.get("suffix", ""), seen))
        )
    if not entries:
        raise HTTPException(status_code=404, detail="Album files are unavailable")
    zip_path = await build_album_zip(entries)
    background_tasks.add_task(os.unlink, zip_path)
    zip_name = f"{sanitize_download_filename(album.get('name') or 'album', 'album')}.zip"
    return await stream_file_with_range(request, zip_path, "application/zip", download_filename=zip_name)


@router.get("/covers/{cover_id}")
async def get_cover(cover_id: str, size: int | None = Query(default=None), db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(require_user)):
    cover_path = None
    if cover_id.startswith("al-"):
        album = await catalog_repo.get_album(db, cover_id[3:])
        cover_path = album.get("coverArtPath") if album else None
    return render_cover_art(cover_path, size=size)
