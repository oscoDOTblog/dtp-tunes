"""Lyrics sidecar persistence and OpenSubsonic XML rendering tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.main import app
from app.routes import api_library, subsonic
from app.services import lyrics as lyrics_service
from app.services.subsonic_format import OPEN_SUBSONIC_EXTENSIONS, ok_envelope, render_envelope


def _request() -> Request:
    return Request({"type": "http", "method": "GET", "headers": [], "query_string": b""})


def _router_paths(router) -> set[str]:
    return {route.path for route in router.routes if hasattr(route, "path")}


def test_read_sidecar_preserves_unicode_and_blank_lines(tmp_path):
    audio = tmp_path / "01 - Song.flac"
    audio.write_bytes(b"audio")
    (tmp_path / "01 - Song.txt").write_bytes("\ufeffFirst line\r\n\r\n日本語\r\n".encode("utf-8"))
    result = lyrics_service.read_sidecar(str(audio))
    assert result.text == "First line\n\n日本語\n"
    assert result.mtime_ns is not None
    assert result.size is not None


def test_read_sidecar_reports_missing_file(tmp_path):
    assert lyrics_service.read_sidecar(str(tmp_path / "missing.mp3")) == lyrics_service.LyricsSidecar(None, None, None)


def test_write_and_delete_sidecar_atomically(tmp_path, monkeypatch):
    audio = tmp_path / "Song.mp3"
    audio.write_bytes(b"audio")
    monkeypatch.setattr(lyrics_service, "resolve_music_path", lambda _relative: str(audio))
    monkeypatch.setattr(lyrics_service, "get_settings", lambda: SimpleNamespace(music_path=str(tmp_path)))
    written = lyrics_service.write_sidecar("Song.mp3", "one\n\ntwo")
    assert written.text == "one\n\ntwo"
    assert (tmp_path / "Song.txt").read_text(encoding="utf-8") == "one\n\ntwo"
    assert not list(tmp_path.glob(".lyrics-*.tmp"))
    lyrics_service.delete_sidecar("Song.mp3")
    assert not (tmp_path / "Song.txt").exists()


def test_lyrics_size_limit_is_measured_as_utf8_bytes():
    with pytest.raises(HTTPException) as exc:
        lyrics_service.normalize_lyrics("é" * (lyrics_service.MAX_LYRICS_BYTES // 2 + 1))
    assert exc.value.status_code == 413


def test_lyrics_routes_and_extension_are_available():
    assert "/api/songs/{song_id}/lyrics" in _router_paths(api_library.router)
    assert "/rest/getLyrics" in _router_paths(subsonic.router)
    assert "/rest/getLyricsBySongId" in _router_paths(subsonic.router)
    assert {"name": "songLyrics", "versions": [1]} in OPEN_SUBSONIC_EXTENSIONS
    assert any(getattr(route, "original_router", None) is api_library.router for route in app.routes)


def test_xml_lyrics_values_are_element_text():
    envelope = ok_envelope({"lyricsList": {"structuredLyrics": [{
        "displayArtist": "Artist", "displayTitle": "Song", "lang": "und", "synced": False,
        "line": [{"value": "First"}, {"value": "日本語"}],
    }]}})
    xml = render_envelope(_request(), {"f": "xml"}, envelope).body.decode("utf-8")
    assert '<structuredLyrics displayArtist="Artist" displayTitle="Song" lang="und" synced="false">' in xml
    assert "<line>First</line>" in xml
    assert "<line>日本語</line>" in xml


def test_xml_classic_lyrics_value_is_element_text():
    envelope = ok_envelope({"lyrics": {"artist": "Artist", "title": "Song", "value": "one\n\ntwo"}})
    xml = render_envelope(_request(), {"f": "xml"}, envelope).body.decode("utf-8")
    assert '<lyrics artist="Artist" title="Song">one\n\ntwo</lyrics>' in xml
