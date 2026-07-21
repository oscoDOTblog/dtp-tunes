from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base import utcnow
from app.security import new_opaque_id


async def create_api_key(
    db: AsyncIOMotorDatabase, *, user_id: str, key_id: str, secret_hash: str, name: str
) -> dict:
    doc = {
        "_id": new_opaque_id(),
        "userId": user_id,
        "keyId": key_id,
        "secretHash": secret_hash,
        "name": name,
        "createdAt": utcnow(),
        "lastUsedAt": None,
        "revokedAt": None,
    }
    await db.apiKeys.insert_one(doc)
    return doc


async def get_by_key_id(db: AsyncIOMotorDatabase, key_id: str) -> dict | None:
    return await db.apiKeys.find_one({"keyId": key_id, "revokedAt": None})


async def list_for_user(db: AsyncIOMotorDatabase, user_id: str) -> list[dict]:
    return await db.apiKeys.find({"userId": user_id}).sort("createdAt", -1).to_list(length=200)


async def touch_last_used(db: AsyncIOMotorDatabase, api_key_id: str) -> None:
    await db.apiKeys.update_one({"_id": api_key_id}, {"$set": {"lastUsedAt": utcnow()}})


async def revoke(db: AsyncIOMotorDatabase, api_key_id: str, user_id: str) -> bool:
    result = await db.apiKeys.update_one(
        {"_id": api_key_id, "userId": user_id, "revokedAt": None},
        {"$set": {"revokedAt": utcnow()}},
    )
    return result.modified_count > 0
