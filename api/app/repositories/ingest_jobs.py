"""Durable, leased MongoDB queue for music ingestion."""

from __future__ import annotations

from datetime import timedelta

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.repositories.base import utcnow
from app.security import new_opaque_id

TERMINAL = {"completed", "failed", "cancelled"}
LEASE_SECONDS = 120


def public_job(doc: dict) -> dict:
    """Return only fields safe for the browser."""
    keys = (
        "mode", "status", "url", "album", "current", "total", "currentTitle",
        "error", "createdAt", "updatedAt", "finishedAt", "retryCount", "scanError",
    )
    result = {"id": doc["_id"], **{key: doc.get(key) for key in keys}}
    result["tracks"] = [
        {"id": track["id"], "title": track["title"]}
        for track in doc.get("tracks") or []
    ] if doc.get("status") == "readyForReview" else []
    return result


async def create(db: AsyncIOMotorDatabase, *, mode: str, url: str, album: dict, cover_name: str | None) -> dict:
    now = utcnow()
    doc = {
        "_id": new_opaque_id(), "mode": mode, "url": url, "album": album,
        "coverName": cover_name, "status": "staging", "current": 0, "total": 0,
        "currentTitle": None, "error": None, "scanError": None, "tracks": [],
        "cancelRequested": False, "retryCount": 0, "leaseOwner": None,
        "leaseExpiresAt": None, "createdAt": now, "updatedAt": now, "finishedAt": None,
    }
    await db.ingestJobs.insert_one(doc)
    return doc


async def get(db: AsyncIOMotorDatabase, job_id: str) -> dict | None:
    return await db.ingestJobs.find_one({"_id": job_id})


async def list_recent(db: AsyncIOMotorDatabase, limit: int = 200) -> list[dict]:
    return await db.ingestJobs.find().sort("createdAt", -1).limit(limit).to_list(length=limit)


async def update(db: AsyncIOMotorDatabase, job_id: str, **fields) -> dict | None:
    return await db.ingestJobs.find_one_and_update(
        {"_id": job_id}, {"$set": {**fields, "updatedAt": utcnow()}},
        return_document=ReturnDocument.AFTER,
    )


async def lease(db: AsyncIOMotorDatabase, owner: str) -> dict | None:
    now = utcnow()
    return await db.ingestJobs.find_one_and_update(
        {"$or": [
            {"status": "queued"},
            {"status": "downloading", "leaseExpiresAt": {"$lt": now}},
        ]},
        {"$set": {
            "status": "downloading", "leaseOwner": owner,
            "leaseExpiresAt": now + timedelta(seconds=LEASE_SECONDS),
            "updatedAt": now, "error": None,
        }},
        sort=[("createdAt", 1)], return_document=ReturnDocument.AFTER,
    )


async def progress(db: AsyncIOMotorDatabase, job_id: str, owner: str, **fields) -> bool:
    now = utcnow()
    result = await db.ingestJobs.update_one(
        {"_id": job_id, "leaseOwner": owner, "status": "downloading", "cancelRequested": False},
        {"$set": {**fields, "leaseExpiresAt": now + timedelta(seconds=LEASE_SECONDS), "updatedAt": now}},
    )
    return result.modified_count > 0


async def finish(db: AsyncIOMotorDatabase, job_id: str, owner: str, **fields) -> bool:
    result = await db.ingestJobs.update_one(
        {"_id": job_id, "leaseOwner": owner, "status": "downloading", "cancelRequested": False},
        {"$set": {**fields, "leaseOwner": None, "leaseExpiresAt": None, "updatedAt": utcnow()}},
    )
    return result.modified_count > 0
