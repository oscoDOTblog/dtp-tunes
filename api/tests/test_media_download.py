"""Tests for download filename helpers and transcode overload behavior (no DB required)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.services import media


def test_sanitize_download_filename_strips_separators():
    assert media.sanitize_download_filename('a/b\\c:d*e?f"g<h>i|j') == "a_b_c_d_e_f_g_h_i_j"


def test_sanitize_download_filename_falls_back_on_empty():
    assert media.sanitize_download_filename("", "track") == "track"
    assert media.sanitize_download_filename("...", "track") == "track"


def test_content_disposition_attachment_has_ascii_and_utf8():
    header = media.content_disposition_attachment("Café Música.mp3")
    assert header.startswith("attachment;")
    assert 'filename="' in header
    assert "filename*=UTF-8''" in header


def test_track_filename_unique_and_prefixed():
    seen: set[str] = set()
    first = media.track_filename("Song", 1, "flac", seen)
    second = media.track_filename("Song", 1, "flac", seen)
    assert first == "01 - Song.flac"
    assert second == "01 - Song (2).flac"


def test_track_filename_without_track_number():
    assert media.track_filename("Song", None, "mp3", set()) == "Song.mp3"


def _fake_request() -> Request:
    scope = {"type": "http", "method": "GET", "headers": [], "query_string": b""}
    return Request(scope)


async def test_stream_with_download_filename_sets_attachment(tmp_path):
    target = tmp_path / "song.mp3"
    target.write_bytes(b"0123456789")
    response = await media.stream_file_with_range(_fake_request(), str(target), "audio/mpeg", download_filename="My Song.mp3")
    assert response.headers["Content-Disposition"].startswith('attachment; filename="My Song.mp3"')
    body = b"".join([chunk async for chunk in response.body_iterator])
    assert body == b"0123456789"


async def test_stream_without_download_filename_has_no_disposition(tmp_path):
    target = tmp_path / "song.mp3"
    target.write_bytes(b"0123456789")
    response = await media.stream_file_with_range(_fake_request(), str(target), "audio/mpeg")
    assert "Content-Disposition" not in response.headers
    body = b"".join([chunk async for chunk in response.body_iterator])
    assert body == b"0123456789"


async def test_transcode_refuses_when_slots_busy(monkeypatch):
    class FakeSettings:
        ffmpeg_max_concurrent = 2
        ffmpeg_queue_timeout_seconds = 0.05

    monkeypatch.setattr(media, "get_settings", lambda: FakeSettings())
    semaphore = media.get_transcode_semaphore()
    # Saturate every permit (settings default is 2, but drain generically).
    acquired = 0
    while not semaphore.locked():
        await semaphore.acquire()
        acquired += 1
    try:
        with pytest.raises(HTTPException) as exc_info:
            await media.transcode_stream("/nonexistent/song.flac", format_="mp3")
        assert exc_info.value.status_code == 503
        assert exc_info.value.headers is not None
        assert "Retry-After" in exc_info.value.headers
    finally:
        for _ in range(acquired):
            semaphore.release()


@pytest.mark.parametrize("range_value,expected,content_range", [
    ("bytes=3-", b"3456789", "bytes 3-9/10"),
    ("bytes=-3", b"789", "bytes 7-9/10"),
    ("bytes=-30", b"0123456789", "bytes 0-9/10"),
    ("bytes=2-4", b"234", "bytes 2-4/10"),
])
async def test_ranges(tmp_path, range_value, expected, content_range):
    target = tmp_path / "song.mp3"
    target.write_bytes(b"0123456789")
    request = Request({"type": "http", "headers": [(b"range", range_value.encode())]})
    response = await media.stream_file_with_range(request, str(target), "audio/mpeg")
    assert response.status_code == 206
    assert response.headers["content-range"] == content_range
    assert int(response.headers["content-length"]) == len(expected)
    assert b"".join([chunk async for chunk in response.body_iterator]) == expected


@pytest.mark.parametrize("range_value", ["bytes=-", "bytes=-0", "bytes=10-", "bytes=4-2", "bytes=0-1,4-5", "bytes=0-1junk"])
async def test_invalid_ranges(tmp_path, range_value):
    target = tmp_path / "song.mp3"
    target.write_bytes(b"0123456789")
    request = Request({"type": "http", "headers": [(b"range", range_value.encode())]})
    with pytest.raises(HTTPException) as exc:
        await media.stream_file_with_range(request, str(target), "audio/mpeg")
    assert exc.value.status_code == 416
    assert exc.value.headers["Content-Range"] == "bytes */10"
