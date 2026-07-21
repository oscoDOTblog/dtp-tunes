"""Byte-range file streaming, download, and concurrency-bounded FFmpeg transcoding."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from collections.abc import AsyncIterator

import aiofiles
from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse

from app.config import get_settings

logger = logging.getLogger("dtp_tunes.media")

_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")
CHUNK_SIZE = 1024 * 256

_transcode_semaphore: asyncio.Semaphore | None = None


def get_transcode_semaphore() -> asyncio.Semaphore:
    global _transcode_semaphore
    if _transcode_semaphore is None:
        _transcode_semaphore = asyncio.Semaphore(get_settings().ffmpeg_max_concurrent)
    return _transcode_semaphore


CONTENT_TYPES = {
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


def content_type_for(suffix: str) -> str:
    return CONTENT_TYPES.get(suffix.lower(), "application/octet-stream")


def resolve_music_path(relative_path: str) -> str:
    """Resolve a stored relative path under MUSIC_PATH with traversal protection."""
    settings = get_settings()
    base = os.path.realpath(settings.music_path)
    candidate = os.path.realpath(os.path.join(base, relative_path))
    if not (candidate == base or candidate.startswith(base + os.sep)):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not os.path.isfile(candidate):
        raise HTTPException(status_code=404, detail="File not found")
    return candidate


async def stream_file_with_range(request: Request, absolute_path: str, content_type: str) -> StreamingResponse:
    """Serve a file honoring an HTTP Range header (required for audio seeking)."""
    file_size = os.path.getsize(absolute_path)
    range_header = request.headers.get("range")

    start, end = 0, file_size - 1
    status_code = 200
    headers = {"Accept-Ranges": "bytes", "Content-Type": content_type}

    if range_header:
        match = _RANGE_RE.match(range_header)
        if not match:
            raise HTTPException(status_code=416, detail="Invalid Range header")
        start_str, end_str = match.groups()
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
        end = min(end, file_size - 1)
        if start > end or start >= file_size:
            raise HTTPException(status_code=416, detail="Range not satisfiable")
        status_code = 206
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"

    content_length = end - start + 1
    headers["Content-Length"] = str(content_length)

    async def iterator() -> AsyncIterator[bytes]:
        async with aiofiles.open(absolute_path, "rb") as f:
            await f.seek(start)
            remaining = content_length
            while remaining > 0:
                chunk = await f.read(min(CHUNK_SIZE, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    return StreamingResponse(iterator(), status_code=status_code, headers=headers, media_type=content_type)


TRANSCODE_FORMATS = {
    "mp3": {"codec": "libmp3lame", "ext": "mp3", "content_type": "audio/mpeg"},
    "opus": {"codec": "libopus", "ext": "opus", "content_type": "audio/opus"},
    "raw": None,
}


async def transcode_stream(
    absolute_path: str, *, format_: str = "mp3", max_bitrate_kbps: int = 192
) -> StreamingResponse:
    """Spawn a bounded, cancellable FFmpeg process and stream stdout as the response body."""
    profile = TRANSCODE_FORMATS.get(format_, TRANSCODE_FORMATS["mp3"])
    if profile is None:
        raise HTTPException(status_code=400, detail="Unsupported transcode format")

    semaphore = get_transcode_semaphore()
    await semaphore.acquire()

    args = [
        "ffmpeg",
        "-i",
        absolute_path,
        "-vn",
        "-map",
        "0:a:0",
        "-c:a",
        profile["codec"],
        "-b:a",
        f"{max_bitrate_kbps}k",
        "-f",
        "mp3" if profile["ext"] == "mp3" else profile["ext"],
        "-loglevel",
        "error",
        "-",
    ]

    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    async def iterator() -> AsyncIterator[bytes]:
        try:
            assert process.stdout is not None
            while True:
                chunk = await process.stdout.read(CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()
            semaphore.release()

    return StreamingResponse(iterator(), media_type=profile["content_type"])
