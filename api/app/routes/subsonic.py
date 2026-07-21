"""OpenSubsonic-compatible REST endpoints (`/rest/*`).

Accepts GET and form-encoded POST, `.view`-suffixed and bare method names,
and returns JSON (default) or XML depending on the `f` parameter. See
docs/SUBSONIC_COMPATIBILITY.md for the tested endpoint/client matrix.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.deps import get_db
from app.repositories import catalog as catalog_repo
from app.repositories import playlists as playlists_repo
from app.repositories import scan_jobs as scan_jobs_repo
from app.repositories import social as social_repo
from app.services import auth_service
from app.services.cover_art import render_cover_art
from app.services.media import content_type_for, resolve_music_path, stream_file_with_range, transcode_stream
from app.services.subsonic_entities import (
    album_to_subsonic,
    artist_to_subsonic,
    genre_to_subsonic,
    playlist_to_subsonic,
    song_to_subsonic,
)
from app.services.subsonic_format import SubsonicError, error_envelope, ok_envelope, render_envelope
from app.routes.subsonic_params import SubsonicParams, parse_params

router = APIRouter(prefix="/rest", tags=["subsonic"])


def endpoint(name: str):
    """Register a handler for both `/name` and `/name.view`, GET and POST."""

    def decorator(func):
        for path in (f"/{name}", f"/{name}.view"):
            func = router.get(path)(func)
            func = router.post(path)(func)
        return func

    return decorator


async def _authenticate(request: Request, db: AsyncIOMotorDatabase, params: SubsonicParams) -> tuple[dict | None, Response | None]:
    username = params.get("u")
    token = params.get("t")
    salt = params.get("s")
    password = params.get("p")
    api_key = params.get("apiKey") or request.headers.get("x-api-key")

    if not (username or api_key):
        return None, render_envelope(request, params.as_dict(), error_envelope(SubsonicError.MISSING_PARAMETER, "Required parameter is missing"))

    user = await auth_service.authenticate_subsonic(
        db, username=username, token=token, salt=salt, password=password, api_key=api_key
    )
    if not user:
        return None, render_envelope(request, params.as_dict(), error_envelope(SubsonicError.WRONG_CREDENTIALS, "Wrong username or password"))
    return user, None


# --------------------------------------------------------------------------
# System / auth
# --------------------------------------------------------------------------


@endpoint("ping")
async def ping(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    _, err = await _authenticate(request, db, params)
    if err:
        return err
    return render_envelope(request, params.as_dict(), ok_envelope())


@endpoint("getLicense")
async def get_license(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    _, err = await _authenticate(request, db, params)
    if err:
        return err
    return render_envelope(request, params.as_dict(), ok_envelope({"license": {"valid": True}}))


@endpoint("getOpenSubsonicExtensions")
async def get_open_subsonic_extensions(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    _, err = await _authenticate(request, db, params)
    if err:
        return err
    from app.services.subsonic_format import OPEN_SUBSONIC_EXTENSIONS

    return render_envelope(request, params.as_dict(), ok_envelope({"openSubsonicExtensions": OPEN_SUBSONIC_EXTENSIONS}))


# --------------------------------------------------------------------------
# Browse (folder-style)
# --------------------------------------------------------------------------


@endpoint("getMusicFolders")
async def get_music_folders(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    from app.config import get_settings

    params = await parse_params(request)
    _, err = await _authenticate(request, db, params)
    if err:
        return err
    settings = get_settings()
    payload = {"musicFolders": {"musicFolder": [{"id": settings.music_folder_id, "name": settings.music_folder_name}]}}
    return render_envelope(request, params.as_dict(), ok_envelope(payload))


@endpoint("getIndexes")
async def get_indexes(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    _, err = await _authenticate(request, db, params)
    if err:
        return err
    artists = await catalog_repo.list_artists(db)
    buckets: dict[str, list[dict]] = {}
    for artist in artists:
        letter = (artist["name"][:1] or "#").upper()
        if not letter.isalpha():
            letter = "#"
        buckets.setdefault(letter, []).append({"id": artist["_id"], "name": artist["name"]})
    index = [{"name": letter, "artist": items} for letter, items in sorted(buckets.items())]
    return render_envelope(request, params.as_dict(), ok_envelope({"indexes": {"lastModified": 0, "index": index}}))


@endpoint("getMusicDirectory")
async def get_music_directory(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    _, err = await _authenticate(request, db, params)
    if err:
        return err
    directory_id = params.get("id")
    if not directory_id:
        return render_envelope(request, params.as_dict(), error_envelope(SubsonicError.MISSING_PARAMETER, "Missing id"))

    artist = await catalog_repo.get_artist(db, directory_id)
    if artist:
        albums = await catalog_repo.list_albums(db, artist_id=directory_id)
        children = [{**album_to_subsonic(a), "isDir": True} for a in albums]
        payload = {"directory": {"id": artist["_id"], "name": artist["name"], "child": children}}
        return render_envelope(request, params.as_dict(), ok_envelope(payload))

    album = await catalog_repo.get_album(db, directory_id)
    if album:
        songs = await catalog_repo.list_songs_by_album(db, directory_id)
        children = [song_to_subsonic(s) for s in songs]
        payload = {"directory": {"id": album["_id"], "name": album["name"], "parent": album.get("artistId"), "child": children}}
        return render_envelope(request, params.as_dict(), ok_envelope(payload))

    return render_envelope(request, params.as_dict(), error_envelope(SubsonicError.NOT_FOUND, "Directory not found"))


# --------------------------------------------------------------------------
# Browse (ID3-tagged)
# --------------------------------------------------------------------------


@endpoint("getArtists")
async def get_artists(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    _, err = await _authenticate(request, db, params)
    if err:
        return err
    artists = await catalog_repo.list_artists(db)
    buckets: dict[str, list[dict]] = {}
    for artist in artists:
        letter = (artist["name"][:1] or "#").upper()
        if not letter.isalpha():
            letter = "#"
        buckets.setdefault(letter, []).append(artist_to_subsonic(artist))
    index = [{"name": letter, "artist": items} for letter, items in sorted(buckets.items())]
    return render_envelope(request, params.as_dict(), ok_envelope({"artists": {"ignoredArticles": "", "index": index}}))


@endpoint("getArtist")
async def get_artist(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    _, err = await _authenticate(request, db, params)
    if err:
        return err
    artist_id = params.get("id")
    artist = await catalog_repo.get_artist(db, artist_id) if artist_id else None
    if not artist:
        return render_envelope(request, params.as_dict(), error_envelope(SubsonicError.NOT_FOUND, "Artist not found"))
    albums = await catalog_repo.list_albums(db, artist_id=artist_id)
    payload = {"artist": {**artist_to_subsonic(artist), "album": [album_to_subsonic(a) for a in albums]}}
    return render_envelope(request, params.as_dict(), ok_envelope(payload))


@endpoint("getAlbum")
async def get_album(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    _, err = await _authenticate(request, db, params)
    if err:
        return err
    album_id = params.get("id")
    album = await catalog_repo.get_album(db, album_id) if album_id else None
    if not album:
        return render_envelope(request, params.as_dict(), error_envelope(SubsonicError.NOT_FOUND, "Album not found"))
    songs = await catalog_repo.list_songs_by_album(db, album_id)
    payload = {"album": {**album_to_subsonic(album), "song": [song_to_subsonic(s) for s in songs]}}
    return render_envelope(request, params.as_dict(), ok_envelope(payload))


@endpoint("getSong")
async def get_song(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    _, err = await _authenticate(request, db, params)
    if err:
        return err
    song_id = params.get("id")
    song = await catalog_repo.get_song(db, song_id) if song_id else None
    if not song:
        return render_envelope(request, params.as_dict(), error_envelope(SubsonicError.NOT_FOUND, "Song not found"))
    return render_envelope(request, params.as_dict(), ok_envelope({"song": song_to_subsonic(song)}))


@endpoint("getGenres")
async def get_genres(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    _, err = await _authenticate(request, db, params)
    if err:
        return err
    genres = await catalog_repo.list_genres(db)
    return render_envelope(request, params.as_dict(), ok_envelope({"genres": {"genre": [genre_to_subsonic(g) for g in genres]}}))


@endpoint("getAlbumList2")
async def get_album_list2(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    _, err = await _authenticate(request, db, params)
    if err:
        return err
    list_type = params.get("type", "alphabeticalByName")
    size = params.get_int("size", 20) or 20
    offset = params.get_int("offset", 0) or 0

    if list_type == "random":
        albums = await catalog_repo.random_albums(db, size)
    elif list_type == "newest":
        albums = await catalog_repo.list_albums(db, skip=offset, limit=size, sort="recent")
    elif list_type == "byGenre":
        genre = params.get("genre", "")
        albums = await db.albums.find({"genre": genre}).skip(offset).limit(size).to_list(length=size)
    elif list_type == "byYear":
        from_year = params.get_int("fromYear", 0) or 0
        to_year = params.get_int("toYear", 9999) or 9999
        lo, hi = min(from_year, to_year), max(from_year, to_year)
        albums = await db.albums.find({"year": {"$gte": lo, "$lte": hi}}).skip(offset).limit(size).to_list(length=size)
    else:
        albums = await catalog_repo.list_albums(db, skip=offset, limit=size, sort="name")

    payload = {"albumList2": {"album": [album_to_subsonic(a) for a in albums]}}
    return render_envelope(request, params.as_dict(), ok_envelope(payload))


@endpoint("getRandomSongs")
async def get_random_songs(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    _, err = await _authenticate(request, db, params)
    if err:
        return err
    size = params.get_int("size", 10) or 10
    genre = params.get("genre")
    songs = await catalog_repo.random_songs(db, size, genre=genre)
    return render_envelope(request, params.as_dict(), ok_envelope({"randomSongs": {"song": [song_to_subsonic(s) for s in songs]}}))


@endpoint("getSongsByGenre")
async def get_songs_by_genre(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    _, err = await _authenticate(request, db, params)
    if err:
        return err
    genre = params.get("genre", "")
    count = params.get_int("count", 10) or 10
    offset = params.get_int("offset", 0) or 0
    songs = await catalog_repo.list_songs_by_genre(db, genre, skip=offset, limit=count)
    return render_envelope(request, params.as_dict(), ok_envelope({"songsByGenre": {"song": [song_to_subsonic(s) for s in songs]}}))


@endpoint("search3")
async def search3(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    user, err = await _authenticate(request, db, params)
    if err:
        return err
    query = params.get("query", "")
    results = await catalog_repo.search_catalog(
        db,
        query,
        artist_limit=params.get_int("artistCount", 20) or 20,
        album_limit=params.get_int("albumCount", 20) or 20,
        song_limit=params.get_int("songCount", 20) or 20,
    )
    starred = await social_repo.starred_ids(db, user["_id"], "song")
    payload = {
        "searchResult3": {
            "artist": [artist_to_subsonic(a) for a in results["artists"]],
            "album": [album_to_subsonic(a) for a in results["albums"]],
            "song": [song_to_subsonic(s, starred_ids=starred) for s in results["songs"]],
        }
    }
    return render_envelope(request, params.as_dict(), ok_envelope(payload))


@endpoint("getStarred2")
async def get_starred2(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    user, err = await _authenticate(request, db, params)
    if err:
        return err
    song_ids = await social_repo.starred_ids(db, user["_id"], "song")
    album_ids = await social_repo.starred_ids(db, user["_id"], "album")
    artist_ids = await social_repo.starred_ids(db, user["_id"], "artist")
    songs = await catalog_repo.get_songs_by_ids(db, list(song_ids))
    albums = [await catalog_repo.get_album(db, a) for a in album_ids]
    artists = [await catalog_repo.get_artist(db, a) for a in artist_ids]
    payload = {
        "starred2": {
            "song": [song_to_subsonic(s, starred_ids=song_ids) for s in songs.values()],
            "album": [album_to_subsonic(a) for a in albums if a],
            "artist": [artist_to_subsonic(a) for a in artists if a],
        }
    }
    return render_envelope(request, params.as_dict(), ok_envelope(payload))


# --------------------------------------------------------------------------
# User state: star, scrobble, play queue
# --------------------------------------------------------------------------


@endpoint("star")
async def star(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    user, err = await _authenticate(request, db, params)
    if err:
        return err
    for song_id in params.get_list("id"):
        await social_repo.star_item(db, user_id=user["_id"], item_id=song_id, item_type="song")
    for album_id in params.get_list("albumId"):
        await social_repo.star_item(db, user_id=user["_id"], item_id=album_id, item_type="album")
    for artist_id in params.get_list("artistId"):
        await social_repo.star_item(db, user_id=user["_id"], item_id=artist_id, item_type="artist")
    return render_envelope(request, params.as_dict(), ok_envelope())


@endpoint("unstar")
async def unstar(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    user, err = await _authenticate(request, db, params)
    if err:
        return err
    for song_id in params.get_list("id"):
        await social_repo.unstar_item(db, user_id=user["_id"], item_id=song_id, item_type="song")
    for album_id in params.get_list("albumId"):
        await social_repo.unstar_item(db, user_id=user["_id"], item_id=album_id, item_type="album")
    for artist_id in params.get_list("artistId"):
        await social_repo.unstar_item(db, user_id=user["_id"], item_id=artist_id, item_type="artist")
    return render_envelope(request, params.as_dict(), ok_envelope())


@endpoint("scrobble")
async def scrobble(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    user, err = await _authenticate(request, db, params)
    if err:
        return err
    submission = params.get_bool("submission", True)
    for song_id in params.get_list("id"):
        if submission:
            await social_repo.record_play(db, user_id=user["_id"], song_id=song_id)
            await catalog_repo.increment_play_count(db, song_id)
    return render_envelope(request, params.as_dict(), ok_envelope())


@endpoint("getPlayQueue")
async def get_play_queue(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    user, err = await _authenticate(request, db, params)
    if err:
        return err
    queue = await social_repo.get_queue(db, user["_id"])
    if not queue:
        return render_envelope(request, params.as_dict(), ok_envelope())
    payload = {
        "playQueue": {
            "current": queue.get("current"),
            "position": queue.get("position", 0),
            "changed": queue.get("changedAt"),
            "changedBy": "dtp-tunes",
            "entry": [song_to_subsonic(s) for s in (await catalog_repo.get_songs_by_ids(db, queue.get("songIds", []))).values()],
        }
    }
    return render_envelope(request, params.as_dict(), ok_envelope(payload))


@endpoint("savePlayQueue")
async def save_play_queue(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    user, err = await _authenticate(request, db, params)
    if err:
        return err
    await social_repo.save_queue(
        db,
        user_id=user["_id"],
        current=params.get("current"),
        position=params.get_int("position", 0) or 0,
        song_ids=params.get_list("id"),
    )
    return render_envelope(request, params.as_dict(), ok_envelope())


# --------------------------------------------------------------------------
# Playlists
# --------------------------------------------------------------------------


@endpoint("getPlaylists")
async def get_playlists(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    user, err = await _authenticate(request, db, params)
    if err:
        return err
    playlists = await playlists_repo.list_playlists_for_user(db, user["_id"])
    return render_envelope(request, params.as_dict(), ok_envelope({"playlists": {"playlist": [playlist_to_subsonic(p) for p in playlists]}}))


@endpoint("getPlaylist")
async def get_playlist(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    _, err = await _authenticate(request, db, params)
    if err:
        return err
    playlist_id = params.get("id")
    playlist = await playlists_repo.get_playlist(db, playlist_id) if playlist_id else None
    if not playlist:
        return render_envelope(request, params.as_dict(), error_envelope(SubsonicError.NOT_FOUND, "Playlist not found"))
    songs_by_id = await catalog_repo.get_songs_by_ids(db, playlist.get("songIds", []))
    ordered_songs = [songs_by_id[sid] for sid in playlist.get("songIds", []) if sid in songs_by_id]
    payload = {"playlist": {**playlist_to_subsonic(playlist), "entry": [song_to_subsonic(s) for s in ordered_songs]}}
    return render_envelope(request, params.as_dict(), ok_envelope(payload))


@endpoint("createPlaylist")
async def create_playlist(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    user, err = await _authenticate(request, db, params)
    if err:
        return err
    playlist_id = params.get("playlistId")
    song_ids = params.get_list("songId") or params.get_list("id")
    if playlist_id:
        await playlists_repo.replace_songs(db, playlist_id, song_ids)
        playlist = await playlists_repo.get_playlist(db, playlist_id)
    else:
        name = params.get("name", "Untitled Playlist")
        playlist = await playlists_repo.create_playlist(
            db, owner_id=user["_id"], name=name, comment=None, public=False, song_ids=song_ids
        )
    payload = {"playlist": playlist_to_subsonic(playlist)}
    return render_envelope(request, params.as_dict(), ok_envelope(payload))


@endpoint("updatePlaylist")
async def update_playlist(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    _, err = await _authenticate(request, db, params)
    if err:
        return err
    playlist_id = params.get("playlistId")
    playlist = await playlists_repo.get_playlist(db, playlist_id) if playlist_id else None
    if not playlist:
        return render_envelope(request, params.as_dict(), error_envelope(SubsonicError.NOT_FOUND, "Playlist not found"))

    await playlists_repo.update_playlist_meta(
        db,
        playlist_id,
        name=params.get("name"),
        comment=params.get("comment"),
        public=params.get_bool("public") if params.get("public") is not None else None,
    )
    song_ids = list(playlist.get("songIds", []))
    remove_indexes = {int(i) for i in params.get_list("songIndexToRemove")}
    song_ids = [s for i, s in enumerate(song_ids) if i not in remove_indexes]
    song_ids.extend(params.get_list("songIdToAdd"))
    await playlists_repo.replace_songs(db, playlist_id, song_ids)
    return render_envelope(request, params.as_dict(), ok_envelope())


@endpoint("deletePlaylist")
async def delete_playlist(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    _, err = await _authenticate(request, db, params)
    if err:
        return err
    playlist_id = params.get("id")
    if playlist_id:
        await playlists_repo.delete_playlist(db, playlist_id)
    return render_envelope(request, params.as_dict(), ok_envelope())


# --------------------------------------------------------------------------
# Users / scan
# --------------------------------------------------------------------------


@endpoint("getUser")
async def get_user(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    user, err = await _authenticate(request, db, params)
    if err:
        return err
    payload = {
        "user": {
            "username": user["username"],
            "adminRole": user.get("role") == "admin",
            "settingsRole": True,
            "downloadRole": True,
            "playlistRole": True,
            "streamRole": True,
            "scrobblingEnabled": True,
        }
    }
    return render_envelope(request, params.as_dict(), ok_envelope(payload))


@endpoint("getScanStatus")
async def get_scan_status(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    _, err = await _authenticate(request, db, params)
    if err:
        return err
    in_progress = await scan_jobs_repo.is_scan_in_progress(db)
    latest = await scan_jobs_repo.latest_job(db)
    count = latest.get("scannedCount", 0) if latest else 0
    payload = {"scanStatus": {"scanning": in_progress, "count": count}}
    return render_envelope(request, params.as_dict(), ok_envelope(payload))


@endpoint("startScan")
async def start_scan(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    user, err = await _authenticate(request, db, params)
    if err:
        return err
    if user.get("role") != "admin":
        return render_envelope(request, params.as_dict(), error_envelope(SubsonicError.NOT_AUTHORIZED, "Admin role required"))
    await scan_jobs_repo.enqueue_scan(db, triggered_by=user["_id"])
    return await get_scan_status(request, db)


# --------------------------------------------------------------------------
# Media: stream, download, cover art
# --------------------------------------------------------------------------


@endpoint("stream")
async def stream(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    _, err = await _authenticate(request, db, params)
    if err:
        return err
    song_id = params.get("id")
    song = await catalog_repo.get_song(db, song_id) if song_id else None
    if not song:
        return render_envelope(request, params.as_dict(), error_envelope(SubsonicError.NOT_FOUND, "Song not found"))

    absolute_path = resolve_music_path(song["path"])
    transcode_format = params.get("format")
    if transcode_format and transcode_format != "raw":
        max_bitrate = params.get_int("maxBitRate", 192) or 192
        return await transcode_stream(absolute_path, format_=transcode_format, max_bitrate_kbps=max_bitrate)

    content_type = content_type_for(song.get("suffix", ""))
    return await stream_file_with_range(request, absolute_path, content_type)


@endpoint("download")
async def download(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    _, err = await _authenticate(request, db, params)
    if err:
        return err
    song_id = params.get("id")
    song = await catalog_repo.get_song(db, song_id) if song_id else None
    if not song:
        return render_envelope(request, params.as_dict(), error_envelope(SubsonicError.NOT_FOUND, "Song not found"))
    absolute_path = resolve_music_path(song["path"])
    content_type = content_type_for(song.get("suffix", ""))
    return await stream_file_with_range(request, absolute_path, content_type)


@endpoint("getCoverArt")
async def get_cover_art(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    params = await parse_params(request)
    _, err = await _authenticate(request, db, params)
    if err:
        return err
    cover_id = params.get("id", "")
    size = params.get_int("size")
    cover_path: str | None = None
    if cover_id.startswith("al-"):
        album = await catalog_repo.get_album(db, cover_id[3:])
        cover_path = album.get("coverArtPath") if album else None
    return render_cover_art(cover_path, size=size)
