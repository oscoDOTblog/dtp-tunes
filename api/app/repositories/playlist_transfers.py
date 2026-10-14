from __future__ import annotations

from datetime import timedelta

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.repositories.base import utcnow
from app.security import new_opaque_id

LEASE_SECONDS = 180


def public_job(doc: dict) -> dict:
    keys = (
        "ownerId",
        "status",
        "sourcePlatform",
        "sourceUrl",
        "source",
        "tracks",
        "current",
        "total",
        "destination",
        "result",
        "error",
        "createdAt",
        "updatedAt",
        "finishedAt",
    )
    return {"id": doc["_id"], **{key: doc.get(key) for key in keys}}


async def create(db: AsyncIOMotorDatabase, owner_id: str, source_url: str) -> dict:
    now = utcnow()
    doc = {
        "_id": new_opaque_id(),
        "ownerId": owner_id,
        "sourcePlatform": "appleMusic",
        "sourceUrl": source_url,
        "source": None,
        "tracks": [],
        "status": "queuedExtraction",
        "current": 0,
        "total": 0,
        "destination": None,
        "result": None,
        "error": None,
        "leaseOwner": None,
        "leaseExpiresAt": None,
        "createdAt": now,
        "updatedAt": now,
        "finishedAt": None,
    }
    await db.playlistTransferJobs.insert_one(doc)
    return doc


async def get(db: AsyncIOMotorDatabase, job_id: str) -> dict | None:
    return await db.playlistTransferJobs.find_one({"_id": job_id})


async def update(db: AsyncIOMotorDatabase, job_id: str, **fields) -> dict | None:
    return await db.playlistTransferJobs.find_one_and_update(
        {"_id": job_id},
        {"$set": {**fields, "updatedAt": utcnow()}},
        return_document=ReturnDocument.AFTER,
    )


async def lease(db: AsyncIOMotorDatabase, owner: str) -> dict | None:
    now = utcnow()
    common = {
        "leaseOwner": owner,
        "leaseExpiresAt": now + timedelta(seconds=LEASE_SECONDS),
        "updatedAt": now,
        "error": None,
    }
    extraction = await db.playlistTransferJobs.find_one_and_update(
        {
            "$or": [
                {"status": "queuedExtraction"},
                {"status": "extracting", "leaseExpiresAt": {"$lt": now}},
            ]
        },
        {"$set": {**common, "status": "extracting"}},
        sort=[("createdAt", 1)],
        return_document=ReturnDocument.AFTER,
    )
    if extraction:
        return extraction
    return await db.playlistTransferJobs.find_one_and_update(
        {
            "$or": [
                {"status": "queuedImport"},
                {"status": "importing", "leaseExpiresAt": {"$lt": now}},
            ]
        },
        {"$set": {**common, "status": "importing"}},
        sort=[("createdAt", 1)],
        return_document=ReturnDocument.AFTER,
    )


async def progress(db: AsyncIOMotorDatabase, job_id: str, owner: str, **fields) -> bool:
    result = await db.playlistTransferJobs.update_one(
        {"_id": job_id, "leaseOwner": owner},
        {
            "$set": {
                **fields,
                "leaseExpiresAt": utcnow() + timedelta(seconds=LEASE_SECONDS),
                "updatedAt": utcnow(),
            }
        },
    )
    return result.modified_count > 0


async def finish(db: AsyncIOMotorDatabase, job_id: str, owner: str, **fields) -> None:
    await db.playlistTransferJobs.update_one(
        {"_id": job_id, "leaseOwner": owner},
        {
            "$set": {
                **fields,
                "leaseOwner": None,
                "leaseExpiresAt": None,
                "updatedAt": utcnow(),
            }
        },
    )
