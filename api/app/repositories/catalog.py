"""Repositories for artists, albums, songs, and genres (the scanned catalog)."""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base import normalize, utcnow
from app.security import new_opaque_id

# --------------------------------------------------------------------------
# Artists
# --------------------------------------------------------------------------


async def upsert_artist(db: AsyncIOMotorDatabase, *, name: str, sort_name: str | None = None) -> dict:
    normalized = normalize(name)
    existing = await db.artists.find_one({"normalizedName": normalized})
    if existing:
        return existing
    doc = {
        "_id": new_opaque_id(),
        "name": name,
        "normalizedName": normalized,
        "sortName": sort_name or name,
        "albumCount": 0,
        "coverArtId": None,
        "createdAt": utcnow(),
        "updatedAt": utcnow(),
    }
    await db.artists.insert_one(doc)
    return doc


async def get_artist(db: AsyncIOMotorDatabase, artist_id: str) -> dict | None:
    return await db.artists.find_one({"_id": artist_id})


async def list_artists(db: AsyncIOMotorDatabase) -> list[dict]:
    return await db.artists.find().sort("sortName", 1).to_list(length=10000)


async def recount_artist_albums(db: AsyncIOMotorDatabase, artist_id: str) -> None:
    count = await db.albums.count_documents({"artistId": artist_id})
    await db.artists.update_one({"_id": artist_id}, {"$set": {"albumCount": count}})


async def set_artist_cover(db: AsyncIOMotorDatabase, artist_id: str, cover_art_id: str) -> None:
    await db.artists.update_one(
        {"_id": artist_id, "coverArtId": None}, {"$set": {"coverArtId": cover_art_id}}
    )


async def sync_artist_album_counts(db: AsyncIOMotorDatabase) -> None:
    """Recompute albumCount for every artist from current albums (after deletions)."""
    counts = await db.albums.aggregate(
        [{"$match": {"artistId": {"$ne": None}}}, {"$group": {"_id": "$artistId", "count": {"$sum": 1}}}]
    ).to_list(length=100000)
    count_by_id = {row["_id"]: row["count"] for row in counts}
    artists = await db.artists.find({}, {"_id": 1}).to_list(length=100000)
    for artist in artists:
        await db.artists.update_one(
            {"_id": artist["_id"]},
            {"$set": {"albumCount": count_by_id.get(artist["_id"], 0)}},
        )


async def delete_orphan_artists(db: AsyncIOMotorDatabase) -> int:
    """Delete artists with no remaining albums.

    Recounts first so stale albumCount values (left behind when orphan albums
    were removed) do not keep empty artists visible in the library.
    """
    await sync_artist_album_counts(db)
    result = await db.artists.delete_many({"albumCount": 0})
    return result.deleted_count


async def reset_library_catalog(db: AsyncIOMotorDatabase) -> dict[str, int]:
    """Wipe scanned library metadata and play-state that references it.

    Preserves users, sessions, and API keys. Clears playlist song membership
    (playlists themselves are kept empty) so remounts start clean.
    """
    songs = await db.songs.delete_many({})
    albums = await db.albums.delete_many({})
    artists = await db.artists.delete_many({})
    genres = await db.genres.delete_many({})
    stars = await db.stars.delete_many({})
    play_history = await db.playHistory.delete_many({})
    play_queues = await db.playQueues.delete_many({})
    scan_jobs = await db.scanJobs.delete_many({})
    playlists_cleared = await db.playlists.update_many(
        {},
        {"$set": {"songIds": [], "updatedAt": utcnow()}},
    )
    return {
        "songs": songs.deleted_count,
        "albums": albums.deleted_count,
        "artists": artists.deleted_count,
        "genres": genres.deleted_count,
        "stars": stars.deleted_count,
        "playHistory": play_history.deleted_count,
        "playQueues": play_queues.deleted_count,
        "scanJobs": scan_jobs.deleted_count,
        "playlistsCleared": playlists_cleared.modified_count,
    }


# --------------------------------------------------------------------------
# Albums
# --------------------------------------------------------------------------


async def upsert_album(
    db: AsyncIOMotorDatabase,
    *,
    name: str,
    artist_id: str | None,
    artist_name: str | None,
    year: int | None,
    genre: str | None,
) -> dict:
    normalized = normalize(name)
    existing = await db.albums.find_one({"normalizedName": normalized, "artistId": artist_id})
    if existing:
        update: dict = {}
        if year and not existing.get("year"):
            update["year"] = year
        if genre and not existing.get("genre"):
            update["genre"] = genre
        if update:
            update["updatedAt"] = utcnow()
            await db.albums.update_one({"_id": existing["_id"]}, {"$set": update})
            existing.update(update)
        return existing
    doc = {
        "_id": new_opaque_id(),
        "name": name,
        "normalizedName": normalized,
        "artistId": artist_id,
        "artistName": artist_name,
        "year": year,
        "genre": genre,
        "coverArtPath": None,
        "songCount": 0,
        "duration": 0,
        "createdAt": utcnow(),
        "updatedAt": utcnow(),
    }
    await db.albums.insert_one(doc)
    if artist_id:
        await recount_artist_albums(db, artist_id)
    return doc


async def get_album(db: AsyncIOMotorDatabase, album_id: str) -> dict | None:
    return await db.albums.find_one({"_id": album_id})


async def list_albums(
    db: AsyncIOMotorDatabase,
    *,
    artist_id: str | None = None,
    skip: int = 0,
    limit: int = 500,
    sort: str = "name",
) -> list[dict]:
    query: dict = {}
    if artist_id:
        query["artistId"] = artist_id
    sort_field = {"name": "normalizedName", "recent": "createdAt", "year": "year"}.get(sort, "normalizedName")
    direction = -1 if sort in {"recent"} else 1
    return await db.albums.find(query).sort(sort_field, direction).skip(skip).limit(limit).to_list(length=limit)


async def count_albums(db: AsyncIOMotorDatabase) -> int:
    return await db.albums.count_documents({})


async def random_albums(db: AsyncIOMotorDatabase, size: int) -> list[dict]:
    return await db.albums.aggregate([{"$sample": {"size": size}}]).to_list(length=size)


async def recount_album_songs(db: AsyncIOMotorDatabase, album_id: str) -> None:
    songs = await db.songs.find({"albumId": album_id}).to_list(length=100000)
    duration = sum(s.get("duration", 0) for s in songs)
    await db.albums.update_one(
        {"_id": album_id}, {"$set": {"songCount": len(songs), "duration": duration, "updatedAt": utcnow()}}
    )


async def set_album_cover_path(db: AsyncIOMotorDatabase, album_id: str, cover_art_path: str) -> None:
    await db.albums.update_one({"_id": album_id}, {"$set": {"coverArtPath": cover_art_path}})


async def delete_orphan_albums(db: AsyncIOMotorDatabase) -> int:
    result = await db.albums.delete_many({"songCount": 0})
    return result.deleted_count


# --------------------------------------------------------------------------
# Songs
# --------------------------------------------------------------------------


async def upsert_song_by_path(db: AsyncIOMotorDatabase, *, path: str, fields: dict) -> tuple[dict, bool]:
    """Insert or update a song keyed by its unique relative path. Returns (doc, created)."""
    now = utcnow()
    existing = await db.songs.find_one({"path": path})
    if existing:
        fields["updatedAt"] = now
        await db.songs.update_one({"_id": existing["_id"]}, {"$set": fields})
        existing.update(fields)
        return existing, False
    doc = {
        "_id": new_opaque_id(),
        "path": path,
        "playCount": 0,
        "createdAt": now,
        "updatedAt": now,
        **fields,
    }
    await db.songs.insert_one(doc)
    return doc, True


async def get_song(db: AsyncIOMotorDatabase, song_id: str) -> dict | None:
    return await db.songs.find_one({"_id": song_id})


async def get_songs_by_ids(db: AsyncIOMotorDatabase, song_ids: list[str]) -> dict[str, dict]:
    if not song_ids:
        return {}
    docs = await db.songs.find({"_id": {"$in": song_ids}}).to_list(length=len(song_ids))
    return {d["_id"]: d for d in docs}


async def list_songs_by_album(db: AsyncIOMotorDatabase, album_id: str) -> list[dict]:
    return await db.songs.find({"albumId": album_id}).sort("track", 1).to_list(length=10000)


async def list_songs_by_genre(db: AsyncIOMotorDatabase, genre: str, *, skip: int = 0, limit: int = 500) -> list[dict]:
    return await db.songs.find({"genre": genre}).skip(skip).limit(limit).to_list(length=limit)


async def random_songs(db: AsyncIOMotorDatabase, size: int, *, genre: str | None = None) -> list[dict]:
    match: dict = {}
    if genre:
        match["genre"] = genre
    pipeline = ([{"$match": match}] if match else []) + [{"$sample": {"size": size}}]
    return await db.songs.aggregate(pipeline).to_list(length=size)


async def search_catalog(db: AsyncIOMotorDatabase, query: str, *, artist_limit: int, album_limit: int, song_limit: int) -> dict:
    pattern = {"$regex": normalize(query), "$options": "i"}
    artists = await db.artists.find({"normalizedName": pattern}).limit(artist_limit).to_list(length=artist_limit)
    albums = await db.albums.find({"normalizedName": pattern}).limit(album_limit).to_list(length=album_limit)
    songs = await db.songs.find({"normalizedTitle": pattern}).limit(song_limit).to_list(length=song_limit)
    return {"artists": artists, "albums": albums, "songs": songs}


async def all_song_paths(db: AsyncIOMotorDatabase) -> set[str]:
    cursor = db.songs.find({}, {"path": 1})
    return {doc["path"] async for doc in cursor}


async def delete_songs_by_paths(db: AsyncIOMotorDatabase, paths: list[str]) -> list[dict]:
    """Delete songs whose path no longer exists on disk; returns deleted docs for cleanup."""
    if not paths:
        return []
    docs = await db.songs.find({"path": {"$in": paths}}).to_list(length=len(paths))
    await db.songs.delete_many({"path": {"$in": paths}})
    return docs


async def increment_play_count(db: AsyncIOMotorDatabase, song_id: str) -> None:
    await db.songs.update_one({"_id": song_id}, {"$inc": {"playCount": 1}})


# --------------------------------------------------------------------------
# Genres
# --------------------------------------------------------------------------


async def upsert_genre(db: AsyncIOMotorDatabase, name: str) -> None:
    if not name:
        return
    await db.genres.update_one({"name": name}, {"$setOnInsert": {"name": name}}, upsert=True)


async def recount_genres(db: AsyncIOMotorDatabase) -> None:
    """Recompute songCount/albumCount for every genre from current catalog state."""
    song_genres = await db.songs.aggregate(
        [{"$match": {"genre": {"$ne": None}}}, {"$group": {"_id": "$genre", "count": {"$sum": 1}}}]
    ).to_list(length=10000)
    album_genres = await db.albums.aggregate(
        [{"$match": {"genre": {"$ne": None}}}, {"$group": {"_id": "$genre", "count": {"$sum": 1}}}]
    ).to_list(length=10000)
    song_counts = {g["_id"]: g["count"] for g in song_genres}
    album_counts = {g["_id"]: g["count"] for g in album_genres}
    names = set(song_counts) | set(album_counts)
    for name in names:
        await db.genres.update_one(
            {"name": name},
            {
                "$set": {
                    "songCount": song_counts.get(name, 0),
                    "albumCount": album_counts.get(name, 0),
                },
                "$setOnInsert": {"name": name},
            },
            upsert=True,
        )
    await db.genres.delete_many({"name": {"$nin": list(names)}})


async def list_genres(db: AsyncIOMotorDatabase) -> list[dict]:
    return await db.genres.find().sort("name", 1).to_list(length=10000)
