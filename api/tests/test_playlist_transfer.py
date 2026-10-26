import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient

from app.config import Settings
from app.deps import require_user
from app.main import app
from app.routes import api_playlist_transfers
from app.services.apple_music import developer_token, parse_playlist_url
from app.services.playlist_matching import rank_candidates, score_candidate
from app.services.youtube import parse_duration


def test_parses_public_apple_playlist_url():
    assert parse_playlist_url(
        "https://music.apple.com/us/playlist/favorites/pl.123abc?l=en"
    ) == ("us", "pl.123abc")


@pytest.mark.parametrize(
    "url",
    [
        "http://music.apple.com/us/playlist/name/pl.123",
        "https://example.com/us/playlist/name/pl.123",
        "https://music.apple.com/us/album/name/123",
        "https://music.apple.com/us/playlist/name/p.123",
    ],
)
def test_rejects_unsupported_apple_urls(url):
    with pytest.raises(ValueError):
        parse_playlist_url(url)


def test_developer_token_is_es256_jwt():
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    settings = Settings(
        app_encryption_key="x" * 32,
        apple_music_team_id="TEAM",
        apple_music_key_id="KEY",
        apple_music_private_key=pem,
    )
    token = developer_token(settings, now=1_700_000_000)
    assert len(token.split(".")) == 3


def test_official_close_duration_match_wins_over_cover():
    track = {"title": "A Great Song", "artist": "The Artist", "durationMs": 201_000}
    candidates = [
        {
            "videoId": "cover",
            "title": "A Great Song cover karaoke",
            "channelTitle": "Someone",
            "durationSeconds": 201,
        },
        {
            "videoId": "official",
            "title": "The Artist - A Great Song (Official Audio)",
            "channelTitle": "The Artist - Topic",
            "durationSeconds": 203,
        },
    ]
    ranked, match, confidence = rank_candidates(track, candidates)
    assert ranked[0]["videoId"] == "official"
    assert match["videoId"] == "official"
    assert confidence == "high"
    assert score_candidate(track, candidates[0]) < score_candidate(track, candidates[1])


def test_weak_candidate_stays_unmatched():
    _, match, confidence = rank_candidates(
        {"title": "Song", "artist": "Artist", "durationMs": 180_000},
        [
            {
                "videoId": "x",
                "title": "Unrelated vlog",
                "channelTitle": "Creator",
                "durationSeconds": 900,
            }
        ],
    )
    assert match is None
    assert confidence == "unmatched"


@pytest.mark.parametrize(
    ("value", "seconds"), [("PT3M21S", 201), ("PT1H2M3S", 3723), ("bad", None)]
)
def test_duration_parser(value, seconds):
    assert parse_duration(value) == seconds


def test_playlist_transfer_routes_are_registered():
    paths = {route.path for route in api_playlist_transfers.router.routes}
    assert "/api/playlist-transfers/status" in paths
    assert "/api/playlist-transfers/{job_id}/confirm" in paths
    assert any(
        getattr(route, "original_router", None) is api_playlist_transfers.router
        for route in app.routes
    )


def test_playlist_transfer_status_requires_admin():
    app.dependency_overrides[require_user] = lambda: {"role": "user"}
    try:
        response = TestClient(app).get("/api/playlist-transfers/status")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
