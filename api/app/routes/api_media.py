"""JSON-API-side media endpoints for the Next.js frontend (cookie-authenticated)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.deps import get_db, require_user
from app.repositories import catalog as catalog_repo
from app.services.cover_art import render_cover_art
from app.services.media import content_type_for, resolve_music_path, stream_file_with_range, transcode_stream

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


@router.get("/covers/{cover_id}")
async def get_cover(cover_id: str, size: int | None = Query(default=None), db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(require_user)):
    cover_path = None
    if cover_id.startswith("al-"):
        album = await catalog_repo.get_album(db, cover_id[3:])
        cover_path = album.get("coverArtPath") if album else None
    return render_cover_art(cover_path, size=size)
