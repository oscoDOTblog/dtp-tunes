"""JSON web API for admin: user management, API keys, and scan control."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.deps import get_db, require_admin, require_user
from app.models import (
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyOut,
    LibraryResetOut,
    ScanJobOut,
    ScanJobStatus,
    UserCreate,
    UserOut,
)
from app.repositories import api_keys as api_keys_repo
from app.repositories import catalog as catalog_repo
from app.repositories import scan_jobs as scan_jobs_repo
from app.repositories import users as users_repo
from app.services import auth_service
from app.worker.artwork import clear_cover_cache

router = APIRouter(prefix="/api/admin", tags=["admin"])
keys_router = APIRouter(prefix="/api/api-keys", tags=["api-keys"])


def _user_out(doc: dict) -> UserOut:
    return UserOut(id=doc["_id"], username=doc["username"], role=doc["role"], isActive=doc.get("isActive", True), createdAt=doc["createdAt"])


def _scan_job_out(doc: dict) -> ScanJobOut:
    return ScanJobOut(
        id=doc["_id"], status=ScanJobStatus(doc["status"]), startedAt=doc.get("startedAt"), finishedAt=doc.get("finishedAt"),
        scannedCount=doc.get("scannedCount", 0), addedCount=doc.get("addedCount", 0), updatedCount=doc.get("updatedCount", 0),
        removedCount=doc.get("removedCount", 0), errorCount=doc.get("errorCount", 0), lastError=doc.get("lastError"),
    )


@router.get("/users", response_model=list[UserOut])
async def list_users(db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(require_admin)) -> list[UserOut]:
    return [_user_out(u) for u in await users_repo.list_users(db)]


@router.post("/users", response_model=UserOut)
async def create_user(body: UserCreate, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(require_admin)) -> UserOut:
    existing = await users_repo.get_user_by_username(db, body.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")
    doc = await auth_service.create_user_with_password(db, username=body.username, password=body.password, role=body.role.value)
    return _user_out(doc)


@router.patch("/users/{user_id}/active")
async def set_user_active(user_id: str, is_active: bool, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(require_admin)) -> dict:
    await users_repo.set_active(db, user_id, is_active)
    return {"ok": True}


@router.patch("/users/{user_id}/role")
async def set_user_role(user_id: str, role: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(require_admin)) -> dict:
    if role not in {"admin", "user"}:
        raise HTTPException(status_code=400, detail="Invalid role")
    await users_repo.set_role(db, user_id, role)
    return {"ok": True}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, db: AsyncIOMotorDatabase = Depends(get_db), admin: dict = Depends(require_admin)) -> dict:
    if user_id == admin["_id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    await users_repo.delete_user(db, user_id)
    return {"ok": True}


@router.get("/scan-jobs", response_model=list[ScanJobOut])
async def list_scan_jobs(db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(require_admin)) -> list[ScanJobOut]:
    latest = await scan_jobs_repo.latest_job(db)
    return [_scan_job_out(latest)] if latest else []


@router.post("/scan-jobs", response_model=ScanJobOut)
async def trigger_scan(db: AsyncIOMotorDatabase = Depends(get_db), admin: dict = Depends(require_admin)) -> ScanJobOut:
    doc = await scan_jobs_repo.enqueue_scan(db, triggered_by=admin["_id"])
    return _scan_job_out(doc)


@router.post("/reset-library", response_model=LibraryResetOut)
async def reset_library(
    db: AsyncIOMotorDatabase = Depends(get_db),
    admin: dict = Depends(require_admin),
    rescan: bool = Query(True, description="Enqueue a fresh library scan after wiping catalog metadata"),
) -> LibraryResetOut:
    """Wipe scanned catalog metadata so a remount can rebuild cleanly.

    Keeps users, sessions, and API keys. Clears stars / play history / queues,
    empties playlist song lists, deletes cover cache files, and optionally
    enqueues a new scan.
    """
    counts = await catalog_repo.reset_library_catalog(db)
    covers_cleared = clear_cover_cache()
    scan_job = None
    if rescan:
        scan_job = await scan_jobs_repo.enqueue_scan(db, triggered_by=f"reset:{admin['_id']}")
    return LibraryResetOut(
        **counts,
        coversCleared=covers_cleared,
        rescanEnqueued=scan_job is not None,
        scanJob=_scan_job_out(scan_job) if scan_job else None,
    )


@keys_router.get("", response_model=list[ApiKeyOut])
async def list_api_keys(db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(require_user)) -> list[ApiKeyOut]:
    keys = await api_keys_repo.list_for_user(db, user["_id"])
    return [ApiKeyOut(id=k["_id"], keyId=k["keyId"], name=k["name"], createdAt=k["createdAt"], lastUsedAt=k.get("lastUsedAt"), revokedAt=k.get("revokedAt")) for k in keys]


@keys_router.post("", response_model=ApiKeyCreated)
async def create_api_key(body: ApiKeyCreate, db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(require_user)) -> ApiKeyCreated:
    record, full_key = await auth_service.create_api_key(db, user_id=user["_id"], name=body.name)
    return ApiKeyCreated(id=record["_id"], keyId=record["keyId"], name=record["name"], createdAt=record["createdAt"], fullKey=full_key)


@keys_router.delete("/{api_key_id}")
async def revoke_api_key(api_key_id: str, db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(require_user)) -> dict:
    revoked = await api_keys_repo.revoke(db, api_key_id, user["_id"])
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"ok": True}
