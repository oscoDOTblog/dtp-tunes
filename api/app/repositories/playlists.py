from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base import utcnow
from app.security import new_opaque_id


async def create_playlist(
    db: AsyncIOMotorDatabase, *, owner_id: str, name: str, comment: str | None, public: bool, song_ids: list[str]
) -> dict:
    now = utcnow()
    doc = {
        "_id": new_opaque_id(),
        "ownerId": owner_id,
        "name": name,
        "comment": comment,
        "public": public,
        "songIds": song_ids,
        "createdAt": now,
        "updatedAt": now,
    }
    await db.playlists.insert_one(doc)
    return doc


async def get_playlist(db: AsyncIOMotorDatabase, playlist_id: str) -> dict | None:
    return await db.playlists.find_one({"_id": playlist_id})


async def list_playlists_for_user(
    db: AsyncIOMotorDatabase, user_id: str, *, sort: str = "name"
) -> list[dict]:
    cursor = db.playlists.find({"$or": [{"ownerId": user_id}, {"public": True}]})
    if sort == "recent":
        return await cursor.sort("updatedAt", -1).to_list(length=10000)
    return await cursor.sort("name", 1).to_list(length=10000)


async def update_playlist_meta(
    db: AsyncIOMotorDatabase, playlist_id: str, *, name: str | None, comment: str | None, public: bool | None
) -> None:
    update: dict = {"updatedAt": utcnow()}
    if name is not None:
        update["name"] = name
    if comment is not None:
        update["comment"] = comment
    if public is not None:
        update["public"] = public
    await db.playlists.update_one({"_id": playlist_id}, {"$set": update})


async def replace_songs(db: AsyncIOMotorDatabase, playlist_id: str, song_ids: list[str]) -> None:
    await db.playlists.update_one({"_id": playlist_id}, {"$set": {"songIds": song_ids, "updatedAt": utcnow()}})


async def delete_playlist(db: AsyncIOMotorDatabase, playlist_id: str) -> None:
    await db.playlists.delete_one({"_id": playlist_id})
