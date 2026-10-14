from __future__ import annotations

import re
from urllib.parse import urlencode

import httpx

from app.config import Settings
from app.security import EncryptedSecret, decrypt_secret

SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
API = "https://www.googleapis.com/youtube/v3"


class YouTubeError(RuntimeError):
    pass


def redirect_uri(settings: Settings) -> str:
    return f"{settings.app_public_url.rstrip('/')}/api/playlist-transfers/oauth/youtube/callback"


def authorization_url(settings: Settings, state: str) -> str:
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise YouTubeError("Google OAuth credentials are not configured")
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(
        {
            "client_id": settings.google_oauth_client_id,
            "redirect_uri": redirect_uri(settings),
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
        }
    )


async def exchange_code(settings: Settings, code: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri(settings),
            },
        )
    if response.is_error:
        raise YouTubeError("Google authorization could not be completed")
    return response.json()


async def access_token(settings: Settings, connection: dict) -> str:
    refresh = decrypt_secret(
        EncryptedSecret.from_doc(connection["refreshTokenEncrypted"])
    )
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "refresh_token": refresh,
                "grant_type": "refresh_token",
            },
        )
    if response.is_error:
        raise YouTubeError("YouTube authorization expired; reconnect your account")
    return response.json()["access_token"]


async def api_request(
    token: str,
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json: dict | None = None,
) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.request(
            method,
            f"{API}/{path}",
            params=params,
            json=json,
            headers={"Authorization": f"Bearer {token}"},
        )
    if response.is_error:
        reason = ""
        try:
            reason = response.json().get("error", {}).get("message", "")
        except Exception:
            pass
        raise YouTubeError(
            reason or f"YouTube API request failed ({response.status_code})"
        )
    return response.json() if response.content else {}


async def search_candidates(token: str, query: str) -> list[dict]:
    result = await api_request(
        token,
        "GET",
        "search",
        params={"part": "snippet", "q": query, "type": "video", "maxResults": 5},
    )
    candidates = [
        {
            "videoId": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "channelTitle": item["snippet"]["channelTitle"],
            "thumbnailUrl": (
                (item["snippet"].get("thumbnails") or {}).get("medium") or {}
            ).get("url"),
            "durationSeconds": None,
        }
        for item in result.get("items", [])
        if item.get("id", {}).get("videoId")
    ]
    if candidates:
        videos = await api_request(
            token,
            "GET",
            "videos",
            params={
                "part": "contentDetails",
                "id": ",".join(c["videoId"] for c in candidates),
            },
        )
        durations = {
            item["id"]: parse_duration(
                item.get("contentDetails", {}).get("duration", "")
            )
            for item in videos.get("items", [])
        }
        for candidate in candidates:
            candidate["durationSeconds"] = durations.get(candidate["videoId"])
    return candidates


def parse_duration(value: str) -> int | None:
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value)
    if not match:
        return None
    hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return hours * 3600 + minutes * 60 + seconds


async def list_owned_playlists(token: str) -> list[dict]:
    items: list[dict] = []
    page: str | None = None
    while True:
        params = {"part": "snippet,status", "mine": "true", "maxResults": 50}
        if page:
            params["pageToken"] = page
        result = await api_request(token, "GET", "playlists", params=params)
        items.extend(
            {
                "id": item["id"],
                "name": item["snippet"]["title"],
                "privacyStatus": item.get("status", {}).get("privacyStatus", "private"),
            }
            for item in result.get("items", [])
        )
        page = result.get("nextPageToken")
        if not page:
            return items


async def create_playlist(token: str, name: str) -> str:
    result = await api_request(
        token,
        "POST",
        "playlists",
        params={"part": "snippet,status"},
        json={"snippet": {"title": name}, "status": {"privacyStatus": "private"}},
    )
    return result["id"]


async def playlist_video_ids(token: str, playlist_id: str) -> set[str]:
    found: set[str] = set()
    page: str | None = None
    while True:
        params = {"part": "contentDetails", "playlistId": playlist_id, "maxResults": 50}
        if page:
            params["pageToken"] = page
        result = await api_request(token, "GET", "playlistItems", params=params)
        found.update(
            item.get("contentDetails", {}).get("videoId")
            for item in result.get("items", [])
        )
        found.discard(None)
        page = result.get("nextPageToken")
        if not page:
            return found


async def insert_video(token: str, playlist_id: str, video_id: str) -> None:
    await api_request(
        token,
        "POST",
        "playlistItems",
        params={"part": "snippet"},
        json={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }
        },
    )
