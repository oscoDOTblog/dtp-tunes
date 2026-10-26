from __future__ import annotations

import asyncio
import logging
import os
import socket

from app.config import get_settings
from app.db import close_connection, ensure_indexes, get_database
from app.repositories import playlist_transfers
from app.repositories.base import utcnow
from app.services import apple_music, youtube
from app.services.playlist_matching import rank_candidates

logger = logging.getLogger("dtp_tunes.playlist_transfer")


async def connection(db) -> dict:
    doc = await db.integrations.find_one({"_id": "youtube"})
    if not doc:
        raise youtube.YouTubeError(
            "Connect a YouTube account before transferring a playlist"
        )
    return doc


async def extract(db, job: dict, owner: str) -> None:
    source, tracks = await apple_music.fetch_public_playlist(
        get_settings(), job["sourceUrl"]
    )
    token = await youtube.access_token(get_settings(), await connection(db))
    await playlist_transfers.progress(
        db, job["_id"], owner, source=source, tracks=tracks, total=len(tracks)
    )
    for index, track in enumerate(tracks):
        query = f"{track['artist']} {track['title']} official audio"
        candidates = await youtube.search_candidates(token, query)
        ranked, match, confidence = rank_candidates(track, candidates)
        track.update(candidates=ranked, match=match, confidence=confidence)
        await playlist_transfers.progress(
            db, job["_id"], owner, tracks=tracks, current=index + 1
        )
    await playlist_transfers.finish(
        db,
        job["_id"],
        owner,
        status="readyForReview",
        tracks=tracks,
        current=len(tracks),
    )


async def do_import(db, job: dict, owner: str) -> None:
    token = await youtube.access_token(get_settings(), await connection(db))
    destination = job["destination"]
    playlist_id = destination.get("playlistId")
    if not playlist_id:
        playlist_id = await youtube.create_playlist(
            token, destination["newPlaylistName"]
        )
        destination = {
            "playlistId": playlist_id,
            "name": destination["newPlaylistName"],
            "created": True,
        }
        await playlist_transfers.progress(
            db, job["_id"], owner, destination=destination
        )
    existing = await youtube.playlist_video_ids(token, playlist_id)
    result = {"added": 0, "duplicates": 0, "skipped": 0, "unmatched": 0, "failed": 0}
    tracks = job["tracks"]
    for index, track in enumerate(tracks):
        if track.get("importStatus") in {"added", "duplicate", "skipped"}:
            result[
                "duplicates"
                if track["importStatus"] == "duplicate"
                else track["importStatus"]
            ] += 1
            continue
        match = track.get("match")
        if track.get("skipped"):
            track["importStatus"] = "skipped"
            result["skipped"] += 1
        elif not match:
            track["importStatus"] = "unmatched"
            result["unmatched"] += 1
        elif match["videoId"] in existing:
            track["importStatus"] = "duplicate"
            result["duplicates"] += 1
        else:
            try:
                await youtube.insert_video(token, playlist_id, match["videoId"])
                existing.add(match["videoId"])
                track["importStatus"] = "added"
                result["added"] += 1
            except Exception as exc:
                track["importStatus"] = "failed"
                track["error"] = str(exc)[:300]
                result["failed"] += 1
        await playlist_transfers.progress(
            db, job["_id"], owner, tracks=tracks, current=index + 1, result=result
        )
    await playlist_transfers.finish(
        db,
        job["_id"],
        owner,
        status="completed",
        tracks=tracks,
        current=len(tracks),
        result=result,
        destination=destination,
        finishedAt=utcnow(),
    )


async def process(db, job: dict, owner: str) -> None:
    try:
        if job["status"] == "extracting":
            await extract(db, job, owner)
        else:
            await do_import(db, job, owner)
    except Exception as exc:
        logger.exception("Playlist transfer %s failed", job["_id"])
        fallback = (
            "readyForReview"
            if job["status"] == "importing" and job.get("tracks")
            else "failed"
        )
        await playlist_transfers.finish(
            db, job["_id"], owner, status=fallback, error=str(exc)[:1000]
        )


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    await ensure_indexes()
    db = get_database()
    owner = f"{socket.gethostname()}-{os.getpid()}"
    try:
        while True:
            job = await playlist_transfers.lease(db, owner)
            if job:
                await process(db, job, owner)
            else:
                await asyncio.sleep(2)
    finally:
        await close_connection()


if __name__ == "__main__":
    asyncio.run(main())
