"""Tests for download filename helpers in the media service (no DB required)."""

from __future__ import annotations

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
