"""Build OpenSubsonic-shaped entity dicts from our Mongo catalog documents."""

from __future__ import annotations


def _cover_art_id_for_album(album: dict) -> str | None:
    return f"al-{album['_id']}" if album.get("coverArtPath") else None


def song_to_subsonic(song: dict, *, starred_ids: set[str] | None = None) -> dict:
    entry = {
        "id": song["_id"],
        "parent": song.get("albumId"),
        "title": song["title"],
        "album": song.get("albumName"),
        "artist": song.get("artistName"),
        "isDir": False,
        "coverArt": f"al-{song['albumId']}" if song.get("albumId") else None,
        "duration": song.get("duration", 0),
        "bitRate": song.get("bitrate"),
        "track": song.get("track"),
        "discNumber": song.get("discNumber"),
        "year": song.get("year"),
        "genre": song.get("genre"),
        "size": song.get("size"),
        "contentType": song.get("contentType"),
        "suffix": song.get("suffix"),
        "path": song["path"],
        "playCount": song.get("playCount", 0),
        "created": song.get("createdAt"),
        "albumId": song.get("albumId"),
        "artistId": song.get("artistId"),
        "type": "music",
        "musicBrainzId": None,
    }
    if starred_ids and song["_id"] in starred_ids:
        entry["starred"] = song.get("createdAt")
    return {k: v for k, v in entry.items() if v is not None}


def album_to_subsonic(album: dict, *, song_count: int | None = None) -> dict:
    entry = {
        "id": album["_id"],
        "name": album["name"],
        "title": album["name"],
        "artist": album.get("artistName"),
        "artistId": album.get("artistId"),
        "coverArt": _cover_art_id_for_album(album),
        "songCount": song_count if song_count is not None else album.get("songCount", 0),
        "duration": album.get("duration", 0),
        "year": album.get("year"),
        "genre": album.get("genre"),
        "created": album.get("createdAt"),
        "isDir": True,
        "parent": album.get("artistId"),
    }
    return {k: v for k, v in entry.items() if v is not None}


def artist_to_subsonic(artist: dict) -> dict:
    entry = {
        "id": artist["_id"],
        "name": artist["name"],
        "albumCount": artist.get("albumCount", 0),
        "coverArt": f"ar-{artist['_id']}" if artist.get("coverArtId") else None,
    }
    return {k: v for k, v in entry.items() if v is not None}


def genre_to_subsonic(genre: dict) -> dict:
    return {
        "value": genre["name"],
        "songCount": genre.get("songCount", 0),
        "albumCount": genre.get("albumCount", 0),
    }


def playlist_to_subsonic(playlist: dict) -> dict:
    return {
        "id": playlist["_id"],
        "name": playlist["name"],
        "comment": playlist.get("comment"),
        "owner": playlist.get("ownerId"),
        "public": playlist.get("public", False),
        "songCount": len(playlist.get("songIds", [])),
        "duration": playlist.get("duration", 0),
        "created": playlist.get("createdAt"),
        "changed": playlist.get("updatedAt"),
    }
