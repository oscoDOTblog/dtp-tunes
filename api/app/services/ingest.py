"""Staging, tagging, and safe per-file promotion into the music library."""

from __future__ import annotations

import os
import fcntl
import re
import shutil
import tempfile
from pathlib import Path

from fastapi import HTTPException
from mutagen import File as MutagenFile
from mutagen.id3 import APIC, ID3, TALB, TDRC, TIT2, TPE1, TRCK
from mutagen.mp3 import MP3

from app.config import get_settings

MAX_UPLOAD_BYTES = 200 * 1024 * 1024
MAX_UPLOAD_FILES = 50
MAX_COVER_BYTES = 8 * 1024 * 1024
AUDIO_UPLOAD_EXTENSIONS = {".mp3", ".flac", ".m4a", ".ogg", ".opus", ".wav"}


def safe_name(value: str, fallback: str) -> str:
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", value).strip().strip(".")
    return name[:160] or fallback


def job_dir(job_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", job_id):
        raise HTTPException(status_code=400, detail="Invalid job id")
    root = Path(get_settings().ingest_path)
    return root / "jobs" / job_id


def album_dir(artist: str, album: str) -> Path:
    root = Path(get_settings().music_path).resolve()
    target = root / safe_name(artist, "Unknown Artist") / safe_name(album, "Unknown Album")
    if target.resolve() != root and root not in target.resolve().parents:
        raise HTTPException(status_code=400, detail="Invalid album path")
    return target


def _load_audio(path: Path):
    try:
        audio = MutagenFile(path, easy=path.suffix.lower() != ".wav")
        if audio is None:
            raise ValueError("unrecognized audio file")
        if audio.tags is None:
            audio.add_tags()
        return audio
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid audio file: {path.name}") from exc


def read_tags(path: Path) -> dict[str, str]:
    audio = _load_audio(path)

    def first(key: str) -> str:
        id3_keys = {"title": "TIT2", "artist": "TPE1", "album": "TALB", "date": "TDRC"}
        value = audio.tags.get(id3_keys.get(key, key) if path.suffix.lower() == ".wav" else key)
        if getattr(value, "text", None):
            value = value.text
        if isinstance(value, (list, tuple)):
            value = value[0] if value else ""
        return str(value or "").strip()

    return {"title": first("title"), "artist": first("artist"), "album": first("album"), "year": first("date")[:4]}


def tag_track(path: Path, *, title: str, artist: str, album: str, year: str, number: int, cover: bytes | None) -> None:
    audio = _load_audio(path)
    if path.suffix.lower() == ".wav":
        audio.tags["TIT2"] = TIT2(encoding=3, text=title)
        audio.tags["TPE1"] = TPE1(encoding=3, text=artist)
        audio.tags["TALB"] = TALB(encoding=3, text=album)
        audio.tags["TRCK"] = TRCK(encoding=3, text=str(number))
        if year:
            audio.tags["TDRC"] = TDRC(encoding=3, text=year)
    else:
        audio.tags["title"] = [title]
        audio.tags["artist"] = [artist]
        audio.tags["album"] = [album]
        audio.tags["tracknumber"] = [str(number)]
        if year:
            audio.tags["date"] = [year]
    audio.save()
    if cover and path.suffix.lower() == ".mp3":
        mp3 = MP3(path, ID3=ID3)
        if mp3.tags is None:
            mp3.add_tags()
        mp3.tags["APIC:Cover"] = APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover)
        mp3.save(v2_version=3)


def promote_tracks(tracks: list[tuple[Path, str]], *, artist: str, album: str, year: str = "", cover: bytes | None = None) -> Path:
    """Merge audio by filename; never remove unrelated tracks or lyric sidecars."""
    for source, _title in tracks:
        if not source.is_file() or source.suffix.lower() not in AUDIO_UPLOAD_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Invalid staged track")
        _load_audio(source)
    target = album_dir(artist, album)
    target.mkdir(parents=True, exist_ok=True)
    lock = target / ".ingest.lock"
    with lock.open("a+b") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            _promote_locked(target, tracks, artist=artist, album=album, year=year, cover=cover)
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
    return target


def _promote_locked(target: Path, tracks: list[tuple[Path, str]], *, artist: str, album: str, year: str, cover: bytes | None) -> None:
    for source, _title in tracks:
        if not source.is_file() or source.suffix.lower() not in AUDIO_UPLOAD_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Invalid staged track")
    for index, (source, title) in enumerate(tracks, start=1):
        suffix = source.suffix.lower()
        destination = target / f"{index:02d} - {safe_name(title, f'Track {index}')}{suffix}"
        fd, temporary = tempfile.mkstemp(prefix=".ingest-", suffix=suffix, dir=target)
        try:
            with os.fdopen(fd, "wb") as output, source.open("rb") as input_file:
                shutil.copyfileobj(input_file, output)
                output.flush()
                os.fsync(output.fileno())
            tag_track(Path(temporary), title=title, artist=artist, album=album, year=year, number=index, cover=cover)
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    if cover:
        fd, temporary = tempfile.mkstemp(prefix=".cover-", suffix=".jpg", dir=target)
        try:
            with os.fdopen(fd, "wb") as output:
                output.write(cover)
            os.replace(temporary, target / "cover.jpg")
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def cleanup_job(job_id: str) -> None:
    shutil.rmtree(job_dir(job_id), ignore_errors=True)
