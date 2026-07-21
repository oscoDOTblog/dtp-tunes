"""Atomic Mongo-backed scan job leases so only one worker scans at a time."""

from __future__ import annotations

from datetime import timedelta

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base import utcnow
from app.security import new_opaque_id

LEASE_SECONDS = 120


async def enqueue_scan(db: AsyncIOMotorDatabase, *, triggered_by: str | None = None) -> dict:
    doc = {
        "_id": new_opaque_id(),
        "status": "pending",
        "triggeredBy": triggered_by,
        "leaseOwner": None,
        "leaseExpiresAt": None,
        "startedAt": None,
        "finishedAt": None,
        "scannedCount": 0,
        "addedCount": 0,
        "updatedCount": 0,
        "removedCount": 0,
        "errorCount": 0,
        "lastError": None,
        "createdAt": utcnow(),
    }
    await db.scanJobs.insert_one(doc)
    return doc


async def try_lease_next_job(db: AsyncIOMotorDatabase, *, owner: str) -> dict | None:
    """Atomically claim the oldest pending/expired-lease job. Returns None if nothing to do."""
    now = utcnow()
    result = await db.scanJobs.find_one_and_update(
        {
            "status": {"$in": ["pending", "running"]},
            "$or": [{"leaseExpiresAt": None}, {"leaseExpiresAt": {"$lt": now}}],
        },
        {
            "$set": {
                "status": "running",
                "leaseOwner": owner,
                "leaseExpiresAt": now + timedelta(seconds=LEASE_SECONDS),
                "startedAt": now,
            }
        },
        sort=[("createdAt", 1)],
        return_document=True,
    )
    return result


async def renew_lease(db: AsyncIOMotorDatabase, job_id: str, *, owner: str) -> bool:
    now = utcnow()
    result = await db.scanJobs.update_one(
        {"_id": job_id, "leaseOwner": owner},
        {"$set": {"leaseExpiresAt": now + timedelta(seconds=LEASE_SECONDS)}},
    )
    return result.modified_count > 0


async def update_progress(db: AsyncIOMotorDatabase, job_id: str, **counters: int) -> None:
    await db.scanJobs.update_one({"_id": job_id}, {"$inc": counters})


async def complete_job(db: AsyncIOMotorDatabase, job_id: str, *, status: str, last_error: str | None = None) -> None:
    await db.scanJobs.update_one(
        {"_id": job_id},
        {"$set": {"status": status, "finishedAt": utcnow(), "lastError": last_error, "leaseOwner": None, "leaseExpiresAt": None}},
    )


async def latest_job(db: AsyncIOMotorDatabase) -> dict | None:
    return await db.scanJobs.find_one(sort=[("createdAt", -1)])


async def is_scan_in_progress(db: AsyncIOMotorDatabase) -> bool:
    now = utcnow()
    doc = await db.scanJobs.find_one({"status": "running", "leaseExpiresAt": {"$gt": now}})
    return doc is not None
