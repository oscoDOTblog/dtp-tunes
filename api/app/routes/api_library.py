"""JSON web API for the Next.js frontend: browse, search, catalog reads."""

from __future__ import annotations

import asyncio
import os

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.deps import get_db, require_admin, require_user
from app.models import AlbumOut, ArtistOut, GenreOut, LyricsOut, LyricsUpdate, SearchResult, SongOut
from app.repositories import catalog as catalog_repo
from app.repositories import social as social_repo
from app.services.lyrics import LyricsSidecar, delete_sidecar, lyrics_fields, normalize_lyrics, write_sidecar
from app.services.media import resolve_music_path

router = APIRouter(prefix="/api", tags=["library"])


def _delete_song_files(relative_path: str) -> None:
    try:
        audio_path = resolve_music_path(relative_path)
    except HTTPException as exc:
        if exc.status_code == 404:
            return
        raise
    sidecar_path = os.path.splitext(audio_path)[0] + ".txt"
    try:
        os.unlink(audio_path)
        try:
            os.unlink(sidecar_path)
        except FileNotFoundError:
            pass
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Unable to delete media file") from exc


async def _delete_song_records(db: AsyncIOMotorDatabase, song_ids: list[str]) -> None:
    if not song_ids:
        return
    await db.songs.delete_many({"_id": {"$in": song_ids}})
    await db.stars.delete_many({"itemId": {"$in": song_ids}, "itemType": "song"})
    await db.playHistory.delete_many({"songId": {"$in": song_ids}})
    await db.playlists.update_many({}, {"$pull": {"songIds": {"$in": song_ids}}})
    await db.playQueues.update_many({}, {"$pull": {"songIds": {"$in": song_ids}}})
    await db.playQueues.update_many({"current": {"$in": song_ids}}, {"$set": {"current": None, "position": 0}})


def artist_out(doc: dict) -> ArtistOut:
    return ArtistOut(id=doc["_id"], name=doc["name"], sortName=doc.get("sortName", doc["name"]), albumCount=doc.get("albumCount", 0), coverArtId=doc.get("coverArtId"))


def album_out(doc: dict) -> AlbumOut:
    return AlbumOut(
        id=doc["_id"], name=doc["name"], artistId=doc.get("artistId"), artistName=doc.get("artistName"),
        year=doc.get("year"), genre=doc.get("genre"), songCount=doc.get("songCount", 0), duration=doc.get("duration", 0),
        coverArtId=(f"al-{doc['_id']}" if doc.get("coverArtPath") else None), createdAt=doc["createdAt"],
    )


def song_out(doc: dict, starred: set[str] | None = None, *, can_edit_lyrics: bool = False) -> SongOut:
    return SongOut(
        id=doc["_id"], title=doc["title"], albumId=doc.get("albumId"), albumName=doc.get("albumName"),
        artistId=doc.get("artistId"), artistName=doc.get("artistName"), genre=doc.get("genre"), track=doc.get("track"),
        discNumber=doc.get("discNumber"), year=doc.get("year"), duration=doc.get("duration", 0), bitrate=doc.get("bitrate"),
        suffix=doc.get("suffix", ""), contentType=doc.get("contentType", "application/octet-stream"), size=doc.get("size", 0),
        coverArtId=(f"al-{doc['albumId']}" if doc.get("albumId") else None), starred=(doc["_id"] in starred) if starred else False,
        playCount=doc.get("playCount", 0), canEditLyrics=can_edit_lyrics,
    )


@router.get("/artists", response_model=list[ArtistOut])
async def list_artists(db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(require_user)) -> list[ArtistOut]:
    artists = await catalog_repo.list_artists(db)
    return [artist_out(a) for a in artists]


@router.get("/artists/{artist_id}")
async def get_artist(artist_id: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(require_user)) -> dict:
    artist = await catalog_repo.get_artist(db, artist_id)
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")
    albums = await catalog_repo.list_albums(db, artist_id=artist_id, sort="year")
    return {"artist": artist_out(artist), "albums": [album_out(a) for a in albums]}


@router.get("/albums", response_model=list[AlbumOut])
async def list_albums(
    sort: str = Query("name", pattern="^(name|recent|year)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(60, ge=1, le=200),
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(require_user),
) -> list[AlbumOut]:
    albums = await catalog_repo.list_albums(db, skip=skip, limit=limit, sort=sort)
    return [album_out(a) for a in albums]


@router.get("/albums/random", response_model=list[AlbumOut])
async def random_albums(size: int = Query(20, ge=1, le=100), db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(require_user)) -> list[AlbumOut]:
    albums = await catalog_repo.random_albums(db, size)
    return [album_out(a) for a in albums]


@router.get("/albums/{album_id}")
async def get_album(album_id: str, db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(require_user)) -> dict:
    album = await catalog_repo.get_album(db, album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    songs = await catalog_repo.list_songs_by_album(db, album_id)
    starred = await social_repo.starred_ids(db, user["_id"], "song")
    return {"album": album_out(album), "songs": [song_out(s, starred, can_edit_lyrics=user.get("role") == "admin") for s in songs]}


@router.get("/genres", response_model=list[GenreOut])
async def list_genres(db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(require_user)) -> list[GenreOut]:
    genres = await catalog_repo.list_genres(db)
    return [GenreOut(name=g["name"], songCount=g.get("songCount", 0), albumCount=g.get("albumCount", 0)) for g in genres]


@router.get("/songs/random", response_model=list[SongOut])
async def random_songs(size: int = Query(30, ge=1, le=200), genre: str | None = None, db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(require_user)) -> list[SongOut]:
    songs = await catalog_repo.random_songs(db, size, genre=genre)
    starred = await social_repo.starred_ids(db, user["_id"], "song")
    return [song_out(s, starred, can_edit_lyrics=user.get("role") == "admin") for s in songs]


@router.get("/search", response_model=SearchResult)
async def search(q: str = Query(..., min_length=1), db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(require_user)) -> SearchResult:
    results = await catalog_repo.search_catalog(db, q, artist_limit=10, album_limit=20, song_limit=30)
    starred = await social_repo.starred_ids(db, user["_id"], "song")
    return SearchResult(
        artists=[artist_out(a) for a in results["artists"]],
        albums=[album_out(a) for a in results["albums"]],
        songs=[song_out(s, starred, can_edit_lyrics=user.get("role") == "admin") for s in results["songs"]],
    )


@router.get("/starred/songs", response_model=list[SongOut])
async def starred_songs(db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(require_user)) -> list[SongOut]:
    ids = await social_repo.starred_ids(db, user["_id"], "song")
    songs = await catalog_repo.get_songs_by_ids(db, list(ids))
    return [song_out(s, ids, can_edit_lyrics=user.get("role") == "admin") for s in songs.values()]


@router.post("/songs/{song_id}/star")
async def star_song(song_id: str, db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(require_user)) -> dict:
    await social_repo.star_item(db, user_id=user["_id"], item_id=song_id, item_type="song")
    return {"ok": True}


@router.delete("/songs/{song_id}/star")
async def unstar_song(song_id: str, db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(require_user)) -> dict:
    await social_repo.unstar_item(db, user_id=user["_id"], item_id=song_id, item_type="song")
    return {"ok": True}


@router.post("/songs/{song_id}/scrobble")
async def scrobble_song(song_id: str, db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(require_user)) -> dict:
    await social_repo.record_play(db, user_id=user["_id"], song_id=song_id)
    await catalog_repo.increment_play_count(db, song_id)
    return {"ok": True}


@router.get("/songs/{song_id}/lyrics", response_model=LyricsOut)
async def get_song_lyrics(song_id: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(require_user)) -> LyricsOut:
    song = await catalog_repo.get_song(db, song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    return LyricsOut(lyrics=song.get("lyrics"), hasLyrics=song.get("lyrics") is not None)


@router.put("/songs/{song_id}/lyrics", response_model=LyricsOut)
async def put_song_lyrics(
    song_id: str,
    payload: LyricsUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(require_admin),
) -> LyricsOut:
    song = await catalog_repo.get_song(db, song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    text = normalize_lyrics(payload.lyrics)
    sidecar = write_sidecar(song["path"], text)
    await catalog_repo.set_song_lyrics(db, song_id, lyrics_fields(sidecar))
    return LyricsOut(lyrics=text, hasLyrics=True)


@router.delete("/songs/{song_id}/lyrics", response_model=LyricsOut)
async def remove_song_lyrics(
    song_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(require_admin),
) -> LyricsOut:
    song = await catalog_repo.get_song(db, song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    delete_sidecar(song["path"])
    await catalog_repo.set_song_lyrics(db, song_id, lyrics_fields(LyricsSidecar(None, None, None)))
    return LyricsOut(lyrics=None, hasLyrics=False)


@router.delete("/songs/{song_id}")
async def permanently_delete_song(
    song_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(require_admin),
) -> dict:
    song = await catalog_repo.get_song(db, song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    await asyncio.to_thread(_delete_song_files, song["path"])
    await _delete_song_records(db, [song_id])
    if song.get("albumId"):
        await catalog_repo.recount_album_songs(db, song["albumId"])
    await catalog_repo.delete_orphan_albums(db)
    await catalog_repo.delete_orphan_artists(db)
    await catalog_repo.recount_genres(db)
    return {"ok": True}


@router.delete("/albums/{album_id}")
async def permanently_delete_album(
    album_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(require_admin),
) -> dict:
    album = await catalog_repo.get_album(db, album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    songs = await catalog_repo.list_songs_by_album(db, album_id)
    for song in songs:
        await asyncio.to_thread(_delete_song_files, song["path"])
    cover_path = album.get("coverArtPath")
    if cover_path:
        from app.services.cover_art import resolve_cache_path
        cached_cover = resolve_cache_path(cover_path)
        if cached_cover:
            try:
                os.unlink(cached_cover)
            except OSError as exc:
                raise HTTPException(status_code=500, detail="Unable to delete cached album cover") from exc
    await _delete_song_records(db, [song["_id"] for song in songs])
    await db.albums.delete_one({"_id": album_id})
    await db.stars.delete_many({"itemId": album_id, "itemType": "album"})
    await catalog_repo.delete_orphan_artists(db)
    await catalog_repo.recount_genres(db)
    return {"ok": True, "deletedSongs": len(songs)}
