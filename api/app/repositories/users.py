from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base import normalize, utcnow
from app.security import new_opaque_id


async def create_user(
    db: AsyncIOMotorDatabase,
    *,
    username: str,
    password_hash: str,
    role: str,
    subsonic_secret_encrypted: dict,
) -> dict:
    now = utcnow()
    doc = {
        "_id": new_opaque_id(),
        "username": username,
        "normalizedUsername": normalize(username),
        "passwordHash": password_hash,
        "role": role,
        "isActive": True,
        "subsonicSecretEncrypted": subsonic_secret_encrypted,
        "createdAt": now,
        "updatedAt": now,
    }
    await db.users.insert_one(doc)
    return doc


async def get_user_by_id(db: AsyncIOMotorDatabase, user_id: str) -> dict | None:
    return await db.users.find_one({"_id": user_id})


async def get_user_by_username(db: AsyncIOMotorDatabase, username: str) -> dict | None:
    return await db.users.find_one({"normalizedUsername": normalize(username)})


async def list_users(db: AsyncIOMotorDatabase) -> list[dict]:
    return await db.users.find().sort("createdAt", 1).to_list(length=1000)


async def count_users(db: AsyncIOMotorDatabase) -> int:
    return await db.users.count_documents({})


async def set_password(db: AsyncIOMotorDatabase, user_id: str, password_hash: str) -> None:
    await db.users.update_one(
        {"_id": user_id},
        {"$set": {"passwordHash": password_hash, "updatedAt": utcnow()}},
    )


async def set_active(db: AsyncIOMotorDatabase, user_id: str, is_active: bool) -> None:
    await db.users.update_one(
        {"_id": user_id},
        {"$set": {"isActive": is_active, "updatedAt": utcnow()}},
    )


async def set_role(db: AsyncIOMotorDatabase, user_id: str, role: str) -> None:
    await db.users.update_one({"_id": user_id}, {"$set": {"role": role, "updatedAt": utcnow()}})


async def set_subsonic_secret(db: AsyncIOMotorDatabase, user_id: str, subsonic_secret_encrypted: dict) -> None:
    await db.users.update_one(
        {"_id": user_id},
        {"$set": {"subsonicSecretEncrypted": subsonic_secret_encrypted, "updatedAt": utcnow()}},
    )


async def delete_user(db: AsyncIOMotorDatabase, user_id: str) -> None:
    await db.users.delete_one({"_id": user_id})
