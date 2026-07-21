"""JSON web API for the persistent play queue (mirrors Subsonic savePlayQueue/getPlayQueue)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.deps import get_db, require_user
from app.models import PlayQueueOut, PlayQueueSave
from app.repositories import catalog as catalog_repo
from app.repositories import social as social_repo
from app.routes.api_library import song_out

router = APIRouter(prefix="/api/queue", tags=["player"])


@router.get("")
async def get_queue(db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(require_user)) -> dict:
    queue = await social_repo.get_queue(db, user["_id"])
    if not queue:
        return {"queue": PlayQueueOut(current=None, position=0, songIds=[]), "songs": []}
    songs_by_id = await catalog_repo.get_songs_by_ids(db, queue.get("songIds", []))
    ordered = [songs_by_id[sid] for sid in queue.get("songIds", []) if sid in songs_by_id]
    out = PlayQueueOut(current=queue.get("current"), position=queue.get("position", 0), songIds=queue.get("songIds", []), changedAt=queue.get("changedAt"))
    return {"queue": out, "songs": [song_out(s) for s in ordered]}


@router.put("")
async def save_queue(body: PlayQueueSave, db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(require_user)) -> dict:
    await social_repo.save_queue(db, user_id=user["_id"], current=body.current, position=body.position, song_ids=body.songIds)
    return {"ok": True}
