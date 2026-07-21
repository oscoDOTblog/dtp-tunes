"""Tests for dtp-tunes ingest scan auth and scanner hidden-dir skipping."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("APP_ENCRYPTION_KEY", "test-only-encryption-key-32-bytes-minimum")
os.environ.setdefault("ADMIN_PASSWORD", "test-only-admin-password")
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGODB_DB", "DTP_test")
os.environ.setdefault("DTP_TUNES_INGEST_TOKEN", "test-ingest-token")

from app.config import get_settings
from app.worker.scanner import _iter_audio_files


def test_ingest_token_configured():
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.dtp_tunes_ingest_token == "test-ingest-token"
    get_settings.cache_clear()


def test_scanner_skips_hidden_staging_dirs(tmp_path: Path):
    music = tmp_path / "music"
    album = music / "Artist" / "Album"
    album.mkdir(parents=True)
    (album / "01 - Track.mp3").write_bytes(b"ID3")

    staging = music / "Artist" / ".Album.staging-abc"
    staging.mkdir(parents=True)
    (staging / "01 - Hidden.mp3").write_bytes(b"ID3")

    backup = music / "Artist" / ".Album.backup-xyz"
    backup.mkdir(parents=True)
    (backup / "01 - Backup.mp3").write_bytes(b"ID3")

    found = list(_iter_audio_files(str(music)))
    assert any(p.endswith("01 - Track.mp3") for p in found)
    assert not any("staging" in p for p in found)
    assert not any("backup" in p for p in found)
