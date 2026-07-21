"""Repositories for stars, play history, and saved play queues."""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base import utcnow
from app.security import new_opaque_id

# Stars


async def star_item(db: AsyncIOMotorDatabase, *, user_id: str, item_id: str, item_type: str) -> None:
    await db.stars.update_one(
        {"userId": user_id, "itemId": item_id, "itemType": item_type},
        {"$setOnInsert": {"_id": new_opaque_id(), "createdAt": utcnow()}},
        upsert=True,
    )


async def unstar_item(db: AsyncIOMotorDatabase, *, user_id: str, item_id: str, item_type: str) -> None:
    await db.stars.delete_one({"userId": user_id, "itemId": item_id, "itemType": item_type})


async def starred_ids(db: AsyncIOMotorDatabase, user_id: str, item_type: str) -> set[str]:
    cursor = db.stars.find({"userId": user_id, "itemType": item_type}, {"itemId": 1})
    return {doc["itemId"] async for doc in cursor}


# Play history


async def record_play(db: AsyncIOMotorDatabase, *, user_id: str, song_id: str) -> None:
    await db.playHistory.insert_one(
        {"_id": new_opaque_id(), "userId": user_id, "songId": song_id, "playedAt": utcnow()}
    )


async def recent_plays(db: AsyncIOMotorDatabase, user_id: str, limit: int = 50) -> list[dict]:
    return await db.playHistory.find({"userId": user_id}).sort("playedAt", -1).limit(limit).to_list(length=limit)


# Play queues


async def save_queue(
    db: AsyncIOMotorDatabase, *, user_id: str, current: str | None, position: int, song_ids: list[str]
) -> None:
    await db.playQueues.update_one(
        {"userId": user_id},
        {
            "$set": {
                "current": current,
                "position": position,
                "songIds": song_ids,
                "changedAt": utcnow(),
            },
            "$setOnInsert": {"_id": new_opaque_id()},
        },
        upsert=True,
    )


async def get_queue(db: AsyncIOMotorDatabase, user_id: str) -> dict | None:
    return await db.playQueues.find_one({"userId": user_id})
