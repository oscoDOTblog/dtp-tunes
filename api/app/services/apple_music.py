from __future__ import annotations

import base64
import json
import time
from urllib.parse import unquote, urlparse

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from app.config import Settings


class AppleMusicError(RuntimeError):
    pass


def parse_playlist_url(value: str) -> tuple[str, str]:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or parsed.hostname not in {
        "music.apple.com",
        "itunes.apple.com",
    }:
        raise ValueError("Enter a valid public Apple Music playlist URL")
    parts = [unquote(part) for part in parsed.path.split("/") if part]
    try:
        marker = parts.index("playlist")
        playlist_id = parts[marker + 2]
    except (ValueError, IndexError):
        raise ValueError("Apple Music playlist URL is missing a playlist ID") from None
    if not playlist_id.startswith("pl.") or len(playlist_id) > 128:
        raise ValueError("Apple Music playlist URL has an unsupported playlist ID")
    storefront = parts[0].lower() if parts and len(parts[0]) == 2 else ""
    return storefront, playlist_id


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def developer_token(settings: Settings, now: int | None = None) -> str:
    if (
        not settings.apple_music_team_id
        or not settings.apple_music_key_id
        or not settings.apple_music_private_key
    ):
        raise AppleMusicError("Apple Music credentials are not configured")
    timestamp = now or int(time.time())
    header = _b64url(
        json.dumps(
            {"alg": "ES256", "kid": settings.apple_music_key_id}, separators=(",", ":")
        ).encode()
    )
    payload = _b64url(
        json.dumps(
            {
                "iss": settings.apple_music_team_id,
                "iat": timestamp,
                "exp": timestamp + 3600,
            },
            separators=(",", ":"),
        ).encode()
    )
    pem = settings.apple_music_private_key.replace("\\n", "\n").encode()
    key = serialization.load_pem_private_key(pem, password=None)
    signature_der = key.sign(f"{header}.{payload}".encode(), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(signature_der)
    return (
        f"{header}.{payload}.{_b64url(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))}"
    )


async def fetch_public_playlist(
    settings: Settings, source_url: str
) -> tuple[dict, list[dict]]:
    storefront, playlist_id = parse_playlist_url(source_url)
    storefront = storefront or settings.apple_music_default_storefront
    headers = {"Authorization": f"Bearer {developer_token(settings)}"}
    url: str | None = (
        f"https://api.music.apple.com/v1/catalog/{storefront}/playlists/{playlist_id}"
    )
    params: dict | None = {"include": "tracks", "limit[tracks]": "100"}
    tracks: list[dict] = []
    playlist: dict | None = None
    async with httpx.AsyncClient(timeout=30) as client:
        while url:
            response = await client.get(
                url if url.startswith("http") else f"https://api.music.apple.com{url}",
                headers=headers,
                params=params,
            )
            params = None
            if response.status_code in {401, 403, 404}:
                raise AppleMusicError(
                    "This playlist is not available as a public Apple Music catalog playlist"
                )
            response.raise_for_status()
            body = response.json()
            if playlist is None:
                data = body.get("data") or []
                if not data:
                    raise AppleMusicError("Apple Music returned no playlist")
                playlist = data[0]
                relationship = playlist.get("relationships", {}).get("tracks", {})
                page = relationship.get("data", [])
                url = relationship.get("next")
            else:
                page = body.get("data", [])
                url = body.get("next")
            for index, resource in enumerate(page, start=len(tracks)):
                attrs = resource.get("attributes") or {}
                tracks.append(
                    {
                        "index": index,
                        "appleTrackId": resource.get("id"),
                        "title": attrs.get("name") or "Unknown title",
                        "artist": attrs.get("artistName") or "Unknown artist",
                        "album": attrs.get("albumName"),
                        "durationMs": attrs.get("durationInMillis"),
                        "match": None,
                        "candidates": [],
                        "confidence": "unmatched",
                        "skipped": False,
                        "importStatus": None,
                        "error": None,
                    }
                )
    attrs = (playlist or {}).get("attributes") or {}
    return {
        "id": playlist_id,
        "storefront": storefront,
        "name": attrs.get("name") or "Apple Music Playlist",
        "url": source_url,
    }, tracks
