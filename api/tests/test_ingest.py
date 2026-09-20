"""Ingestion safety, merge behavior, and admin route coverage."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from mutagen.id3 import ID3, TIT2
from mutagen.mp3 import MP3

from app.main import app
from app.routes import api_ingest
from app.services import ingest


def _mp3(path: Path) -> None:
    frame = bytes.fromhex("fffb9064") + b"\x00" * 413
    path.write_bytes(frame * 8)
    audio = MP3(path, ID3=ID3)
    audio.add_tags()
    audio.tags["TIT2"] = TIT2(encoding=3, text="Original")
    audio.save(v2_version=3)


def test_merge_preserves_unrelated_tracks_and_lyrics(tmp_path, monkeypatch):
    music = tmp_path / "music"
    music.mkdir()
    monkeypatch.setattr(ingest, "get_settings", lambda: SimpleNamespace(music_path=str(music)))
    source = tmp_path / "source.mp3"
    _mp3(source)
    album = music / "Artist" / "Album"
    album.mkdir(parents=True)
    (album / "99 - Existing.mp3").write_bytes(b"existing")
    (album / "01 - Song.txt").write_text("First\n\nSecond", encoding="utf-8")
    ingest.promote_tracks([(source, "Song")], artist="Artist", album="Album")
    assert (album / "01 - Song.mp3").exists()
    assert (album / "99 - Existing.mp3").read_bytes() == b"existing"
    assert (album / "01 - Song.txt").read_text(encoding="utf-8") == "First\n\nSecond"
    assert not list(album.glob(".ingest-*.mp3"))


def test_invalid_mp3_cannot_replace_existing_track(tmp_path, monkeypatch):
    music = tmp_path / "music"
    music.mkdir()
    monkeypatch.setattr(ingest, "get_settings", lambda: SimpleNamespace(music_path=str(music)))
    source = tmp_path / "bad.mp3"
    source.write_bytes(b"not an mp3")
    album = music / "Artist" / "Album"
    album.mkdir(parents=True)
    (album / "01 - Song.mp3").write_bytes(b"existing")
    with pytest.raises(HTTPException):
        ingest.promote_tracks([(source, "Song")], artist="Artist", album="Album")
    assert (album / "01 - Song.mp3").read_bytes() == b"existing"


@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://localhost/x", "http://host.docker.internal/x", "http://127.0.0.1/x", "http://192.168.1.10/x", "oops"])
def test_rejects_local_or_invalid_urls(url):
    with pytest.raises(HTTPException) as exc:
        api_ingest._check_url(url)
    assert exc.value.status_code == 400


def test_ingest_routes_are_registered():
    paths = {route.path for route in api_ingest.router.routes}
    assert "/api/admin/ingest/jobs" in paths
    assert "/api/admin/ingest/upload" in paths
    assert "/api/admin/ingest/jobs/{job_id}/save" in paths
    assert any(getattr(route, "original_router", None) is api_ingest.router for route in app.routes)


def test_ingest_status_requires_admin(monkeypatch, tmp_path):
    from app.deps import require_user
    app.dependency_overrides[require_user] = lambda: {"role": "user"}
    monkeypatch.setattr(api_ingest, "get_settings", lambda: SimpleNamespace(music_path=str(tmp_path)))
    try:
        response = TestClient(app).get("/api/admin/ingest/status")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
