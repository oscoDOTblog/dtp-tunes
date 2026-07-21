"""JSON web API for playlist CRUD used by the Next.js frontend."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.deps import get_db, require_user
from app.models import PlaylistCreate, PlaylistOut, PlaylistUpdate
from app.repositories import catalog as catalog_repo
from app.repositories import playlists as playlists_repo
from app.routes.api_library import song_out

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


def _cover_art_ids_for_songs(songs_by_id: dict[str, dict], song_ids: list[str], *, limit: int = 4) -> list[str]:
    """Return up to `limit` unique album cover IDs from the playlist's song order."""
    covers: list[str] = []
    seen: set[str] = set()
    for song_id in song_ids:
        song = songs_by_id.get(song_id)
        if not song:
            continue
        album_id = song.get("albumId")
        if not album_id:
            continue
        cover_id = f"al-{album_id}"
        if cover_id in seen:
            continue
        seen.add(cover_id)
        covers.append(cover_id)
        if len(covers) >= limit:
            break
    return covers


def _playlist_out(
    doc: dict,
    *,
    songs_by_id: dict[str, dict] | None = None,
    check_song_id: str | None = None,
) -> PlaylistOut:
    song_ids = list(doc.get("songIds", []))
    covers: list[str] = []
    if songs_by_id is not None:
        covers = _cover_art_ids_for_songs(songs_by_id, song_ids)
    contains: bool | None = None
    if check_song_id is not None:
        contains = check_song_id in song_ids
    return PlaylistOut(
        id=doc["_id"],
        ownerId=doc["ownerId"],
        name=doc["name"],
        comment=doc.get("comment"),
        public=doc.get("public", False),
        songCount=len(song_ids),
        duration=doc.get("duration", 0),
        createdAt=doc["createdAt"],
        updatedAt=doc["updatedAt"],
        coverArtIds=covers,
        containsSong=contains,
    )


async def _songs_for_playlists(db: AsyncIOMotorDatabase, playlists: list[dict]) -> dict[str, dict]:
    song_ids: list[str] = []
    seen: set[str] = set()
    for playlist in playlists:
        for song_id in playlist.get("songIds", []):
            if song_id in seen:
                continue
            seen.add(song_id)
            song_ids.append(song_id)
    return await catalog_repo.get_songs_by_ids(db, song_ids)


@router.get("", response_model=list[PlaylistOut])
async def list_playlists(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
    sort: str = Query(default="name", pattern="^(name|recent)$"),
    song_id: str | None = Query(default=None, alias="songId"),
) -> list[PlaylistOut]:
    playlists = await playlists_repo.list_playlists_for_user(db, user["_id"], sort=sort)
    songs_by_id = await _songs_for_playlists(db, playlists)
    return [_playlist_out(p, songs_by_id=songs_by_id, check_song_id=song_id) for p in playlists]


@router.post("", response_model=PlaylistOut)
async def create_playlist(
    body: PlaylistCreate, db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(require_user)
) -> PlaylistOut:
    doc = await playlists_repo.create_playlist(
        db, owner_id=user["_id"], name=body.name, comment=body.comment, public=body.public, song_ids=body.songIds
    )
    songs_by_id = await catalog_repo.get_songs_by_ids(db, body.songIds)
    return _playlist_out(doc, songs_by_id=songs_by_id)


async def _get_owned_playlist(db: AsyncIOMotorDatabase, playlist_id: str, user: dict) -> dict:
    playlist = await playlists_repo.get_playlist(db, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    if playlist["ownerId"] != user["_id"] and not playlist.get("public"):
        raise HTTPException(status_code=403, detail="Not allowed")
    return playlist


@router.get("/{playlist_id}")
async def get_playlist(
    playlist_id: str, db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(require_user)
) -> dict:
    playlist = await _get_owned_playlist(db, playlist_id, user)
    songs_by_id = await catalog_repo.get_songs_by_ids(db, playlist.get("songIds", []))
    ordered = [songs_by_id[sid] for sid in playlist.get("songIds", []) if sid in songs_by_id]
    return {"playlist": _playlist_out(playlist, songs_by_id=songs_by_id), "songs": [song_out(s) for s in ordered]}


@router.patch("/{playlist_id}", response_model=PlaylistOut)
async def update_playlist(
    playlist_id: str,
    body: PlaylistUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
) -> PlaylistOut:
    playlist = await playlists_repo.get_playlist(db, playlist_id)
    if not playlist or playlist["ownerId"] != user["_id"]:
        raise HTTPException(status_code=404, detail="Playlist not found")

    await playlists_repo.update_playlist_meta(db, playlist_id, name=body.name, comment=body.comment, public=body.public)

    song_ids = list(playlist.get("songIds", []))
    if body.songIndexesToRemove:
        remove = set(body.songIndexesToRemove)
        song_ids = [s for i, s in enumerate(song_ids) if i not in remove]

    if body.songIdsToAdd:
        existing = set(song_ids)
        duplicates = [sid for sid in body.songIdsToAdd if sid in existing]
        if duplicates:
            raise HTTPException(status_code=409, detail="Song is already in this playlist")
        song_ids.extend(body.songIdsToAdd)

    await playlists_repo.replace_songs(db, playlist_id, song_ids)

    updated = await playlists_repo.get_playlist(db, playlist_id)
    songs_by_id = await catalog_repo.get_songs_by_ids(db, updated.get("songIds", []) if updated else [])
    return _playlist_out(updated, songs_by_id=songs_by_id)


@router.delete("/{playlist_id}")
async def delete_playlist(
    playlist_id: str, db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(require_user)
) -> dict:
    playlist = await playlists_repo.get_playlist(db, playlist_id)
    if not playlist or playlist["ownerId"] != user["_id"]:
        raise HTTPException(status_code=404, detail="Playlist not found")
    await playlists_repo.delete_playlist(db, playlist_id)
    return {"ok": True}
