"""Mutagen-based audio tag extraction, tolerant of missing/malformed tags."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

from mutagen import File as MutagenFile

ALLOWED_EXTENSIONS = {".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".wma", ".aiff"}

_SUFFIX_CONTENT_TYPE = {
    "mp3": "audio/mpeg",
    "flac": "audio/flac",
    "m4a": "audio/mp4",
    "aac": "audio/aac",
    "ogg": "audio/ogg",
    "opus": "audio/opus",
    "wav": "audio/wav",
    "wma": "audio/x-ms-wma",
    "aiff": "audio/aiff",
}


@dataclass
class ExtractedTags:
    title: str
    artist: str | None
    album_artist: str | None
    album: str | None
    genre: str | None
    track: int | None
    disc_number: int | None
    year: int | None
    duration: int
    bitrate: int | None
    suffix: str
    content_type: str
    size: int
    embedded_artwork: bytes | None = field(default=None, repr=False)


def _first(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return str(value[0]) if value else None
    return str(value)


def _parse_int_prefix(value: str | None) -> int | None:
    if not value:
        return None
    digits = "".join(ch for ch in value.split("/")[0] if ch.isdigit())
    return int(digits) if digits else None


def is_supported(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in ALLOWED_EXTENSIONS


def extract_tags(absolute_path: str) -> ExtractedTags | None:
    """Returns None if the file can't be parsed as audio (skips it safely)."""
    try:
        audio = MutagenFile(absolute_path)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger("dtp_tunes.worker.tags").warning(
            "mutagen failed for %s: %s", absolute_path, exc
        )
        return None
    if audio is None:
        logging.getLogger("dtp_tunes.worker.tags").warning(
            "mutagen returned None for %s (unreadable or unsupported)", absolute_path
        )
        return None

    tags = audio.tags or {}
    suffix = os.path.splitext(absolute_path)[1].lstrip(".").lower()

    def get(*keys: str) -> str | None:
        for key in keys:
            if key in tags:
                value = _first(tags.get(key))
                if value:
                    return value
        return None

    title = get("TIT2", "title", "\xa9nam") or os.path.splitext(os.path.basename(absolute_path))[0]
    artist = get("TPE1", "artist", "\xa9ART")
    album_artist = get("TPE2", "albumartist", "aART") or artist
    album = get("TALB", "album", "\xa9alb")
    genre = get("TCON", "genre", "\xa9gen")
    track = _parse_int_prefix(get("TRCK", "tracknumber", "trkn"))
    disc = _parse_int_prefix(get("TPOS", "discnumber", "disk"))
    year_raw = get("TDRC", "date", "\xa9day") or get("TYER")
    year = _parse_int_prefix(year_raw[:4] if year_raw else None)

    duration = int(getattr(audio.info, "length", 0) or 0)
    bitrate = int(getattr(audio.info, "bitrate", 0) / 1000) if getattr(audio.info, "bitrate", None) else None
    size = os.path.getsize(absolute_path)

    embedded_artwork = _extract_embedded_artwork(audio)

    return ExtractedTags(
        title=title,
        artist=artist,
        album_artist=album_artist,
        album=album,
        genre=genre,
        track=track,
        disc_number=disc,
        year=year,
        duration=duration,
        bitrate=bitrate,
        suffix=suffix,
        content_type=_SUFFIX_CONTENT_TYPE.get(suffix, "application/octet-stream"),
        size=size,
        embedded_artwork=embedded_artwork,
    )


def _extract_embedded_artwork(audio) -> bytes | None:
    try:
        if hasattr(audio, "pictures") and audio.pictures:
            return audio.pictures[0].data
        tags = audio.tags
        if tags is None:
            return None
        for key in tags.keys():
            if str(key).startswith("APIC"):
                return tags[key].data
        if "covr" in tags:
            covers = tags["covr"]
            if covers:
                return bytes(covers[0])
    except Exception:  # noqa: BLE001
        return None
    return None


def find_sidecar_artwork(directory: str) -> bytes | None:
    for name in ("cover.jpg", "cover.png", "folder.jpg", "folder.png", "front.jpg"):
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate):
            try:
                with open(candidate, "rb") as f:
                    return f.read()
            except OSError:
                continue
    return None
