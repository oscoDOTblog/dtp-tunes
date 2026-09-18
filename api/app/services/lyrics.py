"""Read and atomically write UTF-8 lyric sidecars beside audio files."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass

from fastapi import HTTPException

from app.config import get_settings
from app.services.media import resolve_music_path

MAX_LYRICS_BYTES = 1024 * 1024


@dataclass(frozen=True)
class LyricsSidecar:
    text: str | None
    mtime_ns: int | None
    size: int | None


def sidecar_path_for_audio(audio_path: str) -> str:
    return os.path.splitext(audio_path)[0] + ".txt"


def read_sidecar(audio_path: str) -> LyricsSidecar:
    path = sidecar_path_for_audio(audio_path)
    try:
        stat = os.stat(path)
    except FileNotFoundError:
        return LyricsSidecar(None, None, None)
    if stat.st_size > MAX_LYRICS_BYTES:
        raise ValueError("Lyrics file exceeds the 1 MiB limit")
    with open(path, "r", encoding="utf-8-sig", newline=None) as handle:
        text = handle.read()
    return LyricsSidecar(text, stat.st_mtime_ns, stat.st_size)


def lyrics_fields(sidecar: LyricsSidecar) -> dict:
    return {
        "lyrics": sidecar.text,
        "lyricsMtimeNs": sidecar.mtime_ns,
        "lyricsFileSize": sidecar.size,
    }


def resolve_song_sidecar(relative_audio_path: str) -> str:
    """Resolve a catalog song and ensure its sidecar remains under MUSIC_PATH."""
    audio_path = resolve_music_path(relative_audio_path)
    sidecar_path = sidecar_path_for_audio(audio_path)
    root = os.path.realpath(get_settings().music_path)
    parent = os.path.realpath(os.path.dirname(sidecar_path))
    if not (parent == root or parent.startswith(root + os.sep)):
        raise HTTPException(status_code=400, detail="Invalid lyrics path")
    return sidecar_path


def normalize_lyrics(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if len(normalized.encode("utf-8")) > MAX_LYRICS_BYTES:
        raise HTTPException(status_code=413, detail="Lyrics exceed the 1 MiB limit")
    return normalized


def write_sidecar(relative_audio_path: str, text: str) -> LyricsSidecar:
    path = resolve_song_sidecar(relative_audio_path)
    directory = os.path.dirname(path)
    temp_path: str | None = None
    try:
        fd, temp_path = tempfile.mkstemp(prefix=".lyrics-", suffix=".tmp", dir=directory)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        temp_path = None
        return read_sidecar(resolve_music_path(relative_audio_path))
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Unable to write lyrics sidecar") from exc
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass


def delete_sidecar(relative_audio_path: str) -> None:
    path = resolve_song_sidecar(relative_audio_path)
    try:
        os.unlink(path)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Unable to delete lyrics sidecar") from exc
