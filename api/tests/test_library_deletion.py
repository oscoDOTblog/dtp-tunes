"""Permanent media deletion safety tests."""

from app.routes import api_library


def test_delete_song_files_removes_audio_and_lyrics(tmp_path, monkeypatch):
    audio = tmp_path / "Song.flac"
    lyrics = tmp_path / "Song.txt"
    audio.write_bytes(b"audio")
    lyrics.write_text("lyrics", encoding="utf-8")
    monkeypatch.setattr(api_library, "resolve_music_path", lambda _relative: str(audio))

    api_library._delete_song_files("Artist/Album/Song.flac")

    assert not audio.exists()
    assert not lyrics.exists()


def test_permanent_delete_routes_are_registered():
    routes = {(route.path, next(iter(route.methods))) for route in api_library.router.routes if route.methods}
    assert ("/api/songs/{song_id}", "DELETE") in routes
    assert ("/api/albums/{album_id}", "DELETE") in routes
