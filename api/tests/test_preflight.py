from __future__ import annotations

from app import preflight


def _valid(monkeypatch):
    values = {
        "ADMIN_PASSWORD": "a-secure-admin-password",
        "APP_ENCRYPTION_KEY": "a-secure-encryption-key-at-least-32-bytes",
        "MONGODB_URI": "mongodb://mongodb:27017",
        "MONGODB_DB": "DTP_local",
        "MONGODB_COLLECTION_PREFIX": "tunes_",
        "APP_PUBLIC_URL": "http://localhost:8080",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    for name in (
        "APPLE_MUSIC_TEAM_ID",
        "APPLE_MUSIC_KEY_ID",
        "APPLE_MUSIC_PRIVATE_KEY",
        "GOOGLE_OAUTH_CLIENT_ID",
        "GOOGLE_OAUTH_CLIENT_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)


def test_valid_core_environment_passes_with_optional_warnings(monkeypatch):
    _valid(monkeypatch)
    errors, warnings = preflight.validate_environment()
    assert errors == []
    assert len(warnings) == 2


def test_missing_and_example_core_values_fail(monkeypatch):
    _valid(monkeypatch)
    monkeypatch.setenv("ADMIN_PASSWORD", "changeme-admin-password")
    monkeypatch.setenv("APP_ENCRYPTION_KEY", "replace-with-a-long-random-secret-key-32b")
    monkeypatch.setenv("MONGODB_URI", "mongodb+srv://user:pass@cluster.mongodb.net")
    errors, _ = preflight.validate_environment()
    assert len(errors) == 3


def test_partial_playlist_credentials_warn(monkeypatch):
    _valid(monkeypatch)
    monkeypatch.setenv("APPLE_MUSIC_TEAM_ID", "team")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client")
    errors, warnings = preflight.validate_environment()
    assert errors == []
    assert any("APPLE_MUSIC_KEY_ID" in warning for warning in warnings)
    assert any("GOOGLE_OAUTH_CLIENT_SECRET" in warning for warning in warnings)


def test_mongo_credentials_are_redacted():
    assert (
        preflight._safe_mongo_target("mongodb+srv://real-user:real-password@cluster.host/db")
        == "mongodb+srv://***:***@cluster.host/db"
    )
