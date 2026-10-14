from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.config import Settings, get_settings
from app.deps import get_db, require_admin
from app.models import (
    PlaylistTransferConfirm,
    PlaylistTransferCreate,
    PlaylistTransferMatchUpdate,
    PlaylistTransferSearch,
)
from app.repositories import playlist_transfers
from app.repositories.base import utcnow
from app.security import encrypt_secret, hash_token, new_session_token
from app.services import apple_music, youtube

router = APIRouter(prefix="/api/playlist-transfers", tags=["playlist-transfers"])


async def _owned(db, job_id: str, user: dict) -> dict:
    job = await playlist_transfers.get(db, job_id)
    if not job or job.get("ownerId") != user["_id"]:
        raise HTTPException(404, "Playlist transfer not found")
    return job


@router.get("/status")
async def status(
    db=Depends(get_db),
    settings: Settings = Depends(get_settings),
    _=Depends(require_admin),
):
    connected = await db.integrations.find_one({"_id": "youtube"})
    return {
        "appleMusicConfigured": all(
            [
                settings.apple_music_team_id,
                settings.apple_music_key_id,
                settings.apple_music_private_key,
            ]
        ),
        "youtubeConfigured": all(
            [settings.google_oauth_client_id, settings.google_oauth_client_secret]
        ),
        "youtubeConnected": connected is not None,
        "youtubeChannelTitle": connected.get("channelTitle") if connected else None,
    }


@router.post("/oauth/youtube/start")
async def oauth_start(
    db=Depends(get_db),
    settings: Settings = Depends(get_settings),
    user=Depends(require_admin),
):
    state = new_session_token()
    await db.oauthStates.insert_one(
        {
            "_id": new_session_token(),
            "stateHash": hash_token(state),
            "userId": user["_id"],
            "expiresAt": utcnow() + timedelta(minutes=10),
        }
    )
    try:
        return {"authorizationUrl": youtube.authorization_url(settings, state)}
    except youtube.YouTubeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/oauth/youtube/callback")
async def oauth_callback(
    code: str = Query(),
    state: str = Query(),
    db=Depends(get_db),
    settings: Settings = Depends(get_settings),
    user=Depends(require_admin),
):
    state_doc = await db.oauthStates.find_one_and_delete(
        {
            "stateHash": hash_token(state),
            "userId": user["_id"],
            "expiresAt": {"$gt": utcnow()},
        }
    )
    if not state_doc:
        return RedirectResponse("/import-playlist?oauth=invalid")
    try:
        tokens = await youtube.exchange_code(settings, code)
        refresh = tokens.get("refresh_token")
        if not refresh:
            raise youtube.YouTubeError("Google did not return an offline refresh token")
        encrypted = encrypt_secret(refresh).to_doc()
        access = tokens["access_token"]
        channels = await youtube.api_request(
            access, "GET", "channels", params={"part": "snippet", "mine": "true"}
        )
        channel = (channels.get("items") or [{}])[0]
        await db.integrations.replace_one(
            {"_id": "youtube"},
            {
                "_id": "youtube",
                "ownerId": user["_id"],
                "refreshTokenEncrypted": encrypted,
                "channelId": channel.get("id"),
                "channelTitle": channel.get("snippet", {}).get("title"),
                "updatedAt": utcnow(),
            },
            upsert=True,
        )
        return RedirectResponse("/import-playlist?oauth=connected")
    except Exception:
        return RedirectResponse("/import-playlist?oauth=failed")


@router.delete("/oauth/youtube")
async def disconnect(db=Depends(get_db), _=Depends(require_admin)):
    await db.integrations.delete_one({"_id": "youtube"})
    return {"ok": True}


async def _token(db, settings):
    connection = await db.integrations.find_one({"_id": "youtube"})
    if not connection:
        raise HTTPException(409, "Connect a YouTube account first")
    try:
        return await youtube.access_token(settings, connection)
    except youtube.YouTubeError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.get("/destinations")
async def destinations(
    db=Depends(get_db), settings=Depends(get_settings), _=Depends(require_admin)
):
    try:
        return await youtube.list_owned_playlists(await _token(db, settings))
    except youtube.YouTubeError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.post("")
async def create(
    body: PlaylistTransferCreate, db=Depends(get_db), user=Depends(require_admin)
):
    try:
        apple_music.parse_playlist_url(body.sourceUrl)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if not await db.integrations.find_one({"_id": "youtube"}):
        raise HTTPException(409, "Connect a YouTube account first")
    return playlist_transfers.public_job(
        await playlist_transfers.create(db, user["_id"], body.sourceUrl)
    )


@router.get("/{job_id}")
async def get_job(job_id: str, db=Depends(get_db), user=Depends(require_admin)):
    return playlist_transfers.public_job(await _owned(db, job_id, user))


@router.post("/{job_id}/search")
async def search(
    job_id: str,
    body: PlaylistTransferSearch,
    track_index: int = Query(alias="trackIndex"),
    db=Depends(get_db),
    settings=Depends(get_settings),
    user=Depends(require_admin),
):
    job = await _owned(db, job_id, user)
    if track_index < 0 or track_index >= len(job.get("tracks", [])):
        raise HTTPException(404, "Track not found")
    try:
        candidates = await youtube.search_candidates(
            await _token(db, settings), body.query
        )
        tracks = job["tracks"]
        tracks[track_index]["candidates"] = candidates
        await playlist_transfers.update(db, job_id, tracks=tracks)
        return candidates
    except youtube.YouTubeError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.patch("/{job_id}/tracks/{track_index}")
async def update_match(
    job_id: str,
    track_index: int,
    body: PlaylistTransferMatchUpdate,
    db=Depends(get_db),
    user=Depends(require_admin),
):
    job = await _owned(db, job_id, user)
    if job["status"] != "readyForReview":
        raise HTTPException(409, "Transfer is not ready for review")
    tracks = job.get("tracks", [])
    if track_index < 0 or track_index >= len(tracks):
        raise HTTPException(404, "Track not found")
    track = tracks[track_index]
    if body.skipped:
        track.update(skipped=True, match=None, confidence="skipped")
    elif body.videoId:
        candidate = next(
            (
                item
                for item in track.get("candidates", [])
                if item["videoId"] == body.videoId
            ),
            None,
        )
        if not candidate:
            raise HTTPException(422, "Select a result returned for this track")
        track.update(skipped=False, match=candidate, confidence="manual")
    else:
        track.update(skipped=False, match=None, confidence="unmatched")
    return playlist_transfers.public_job(
        await playlist_transfers.update(db, job_id, tracks=tracks)
    )


@router.post("/{job_id}/confirm")
async def confirm(
    job_id: str,
    body: PlaylistTransferConfirm,
    db=Depends(get_db),
    user=Depends(require_admin),
):
    job = await _owned(db, job_id, user)
    if job["status"] != "readyForReview":
        raise HTTPException(409, "Transfer is not ready for review")
    if bool(body.destinationPlaylistId) == bool(body.newPlaylistName):
        raise HTTPException(
            422, "Choose an existing playlist or enter a new playlist name"
        )
    destination = {
        "playlistId": body.destinationPlaylistId,
        "newPlaylistName": body.newPlaylistName,
    }
    return playlist_transfers.public_job(
        await playlist_transfers.update(
            db,
            job_id,
            status="queuedImport",
            current=0,
            destination=destination,
            error=None,
        )
    )
