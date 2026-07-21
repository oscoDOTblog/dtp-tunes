"""JSON web API for playlist CRUD used by the Next.js frontend."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.deps import get_db, require_user
from app.models import PlaylistCreate, PlaylistOut, PlaylistUpdate
from app.repositories import catalog as catalog_repo
from app.repositories import playlists as playlists_repo
from app.routes.api_library import song_out

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


def _playlist_out(doc: dict) -> PlaylistOut:
    songs = doc.get("songIds", [])
    return PlaylistOut(
        id=doc["_id"], ownerId=doc["ownerId"], name=doc["name"], comment=doc.get("comment"), public=doc.get("public", False),
        songCount=len(songs), duration=doc.get("duration", 0), createdAt=doc["createdAt"], updatedAt=doc["updatedAt"],
    )


@router.get("", response_model=list[PlaylistOut])
async def list_playlists(db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(require_user)) -> list[PlaylistOut]:
    playlists = await playlists_repo.list_playlists_for_user(db, user["_id"])
    return [_playlist_out(p) for p in playlists]


@router.post("", response_model=PlaylistOut)
async def create_playlist(body: PlaylistCreate, db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(require_user)) -> PlaylistOut:
    doc = await playlists_repo.create_playlist(
        db, owner_id=user["_id"], name=body.name, comment=body.comment, public=body.public, song_ids=body.songIds
    )
    return _playlist_out(doc)


async def _get_owned_playlist(db: AsyncIOMotorDatabase, playlist_id: str, user: dict) -> dict:
    playlist = await playlists_repo.get_playlist(db, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    if playlist["ownerId"] != user["_id"] and not playlist.get("public"):
        raise HTTPException(status_code=403, detail="Not allowed")
    return playlist


@router.get("/{playlist_id}")
async def get_playlist(playlist_id: str, db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(require_user)) -> dict:
    playlist = await _get_owned_playlist(db, playlist_id, user)
    songs_by_id = await catalog_repo.get_songs_by_ids(db, playlist.get("songIds", []))
    ordered = [songs_by_id[sid] for sid in playlist.get("songIds", []) if sid in songs_by_id]
    return {"playlist": _playlist_out(playlist), "songs": [song_out(s) for s in ordered]}


@router.patch("/{playlist_id}", response_model=PlaylistOut)
async def update_playlist(playlist_id: str, body: PlaylistUpdate, db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(require_user)) -> PlaylistOut:
    playlist = await playlists_repo.get_playlist(db, playlist_id)
    if not playlist or playlist["ownerId"] != user["_id"]:
        raise HTTPException(status_code=404, detail="Playlist not found")

    await playlists_repo.update_playlist_meta(db, playlist_id, name=body.name, comment=body.comment, public=body.public)

    song_ids = list(playlist.get("songIds", []))
    if body.songIndexesToRemove:
        remove = set(body.songIndexesToRemove)
        song_ids = [s for i, s in enumerate(song_ids) if i not in remove]
    song_ids.extend(body.songIdsToAdd)
    await playlists_repo.replace_songs(db, playlist_id, song_ids)

    updated = await playlists_repo.get_playlist(db, playlist_id)
    return _playlist_out(updated)


@router.delete("/{playlist_id}")
async def delete_playlist(playlist_id: str, db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(require_user)) -> dict:
    playlist = await playlists_repo.get_playlist(db, playlist_id)
    if not playlist or playlist["ownerId"] != user["_id"]:
        raise HTTPException(status_code=404, detail="Playlist not found")
    await playlists_repo.delete_playlist(db, playlist_id)
    return {"ok": True}
