from __future__ import annotations

from datetime import timedelta

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base import utcnow
from app.security import hash_token, new_opaque_id


async def create_session(
    db: AsyncIOMotorDatabase, *, user_id: str, token: str, ttl_seconds: int, user_agent: str | None
) -> dict:
    now = utcnow()
    doc = {
        "_id": new_opaque_id(),
        "userId": user_id,
        "tokenHash": hash_token(token),
        "userAgent": user_agent,
        "createdAt": now,
        "expiresAt": now + timedelta(seconds=ttl_seconds),
    }
    await db.sessions.insert_one(doc)
    return doc


async def get_session_by_token(db: AsyncIOMotorDatabase, token: str) -> dict | None:
    return await db.sessions.find_one({"tokenHash": hash_token(token), "expiresAt": {"$gt": utcnow()}})


async def delete_session(db: AsyncIOMotorDatabase, token: str) -> None:
    await db.sessions.delete_one({"tokenHash": hash_token(token)})


async def delete_all_sessions_for_user(db: AsyncIOMotorDatabase, user_id: str) -> None:
    await db.sessions.delete_many({"userId": user_id})
